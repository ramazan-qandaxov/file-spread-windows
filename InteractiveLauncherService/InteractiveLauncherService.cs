// InteractiveLauncherService.cs
// WARNING: Use only in isolated, authorized lab VMs.
// Builds: target net8.0-windows / win-x64 and run as LocalSystem service.

using System;
using System.Diagnostics;
using System.Linq;
using System.Runtime.InteropServices;
using System.ServiceProcess;
using System.Text;

public class InteractiveLauncherService : ServiceBase
{
    // Token / access constants
    const int TOKEN_ASSIGN_PRIMARY = 0x0001;
    const int TOKEN_DUPLICATE = 0x0002;
    const int TOKEN_QUERY = 0x0008;
    const int TOKEN_ADJUST_DEFAULT = 0x0080;
    const int TOKEN_ALL_ACCESS = 0xF01FF;

    const uint CREATE_UNICODE_ENVIRONMENT = 0x00000400;
    const uint CREATE_NEW_CONSOLE = 0x00000010;

    public InteractiveLauncherService()
    {
        this.ServiceName = "InteractiveLauncherService";
        this.CanHandleSessionChangeEvent = true;
        this.CanStop = true;
    }

    protected override void OnStart(string[] args)
    {
        try
        {
            EventLog.WriteEntry("InteractiveLauncherService starting.", EventLogEntryType.Information);
        }
        catch { /* best-effort logging */ }

        // Optionally: attempt to launch in the active session on service start
        TryLaunchInActiveConsoleSession();
    }

    protected override void OnStop()
    {
        try
        {
            EventLog.WriteEntry("InteractiveLauncherService stopping.", EventLogEntryType.Information);
        }
        catch { }
    }

    protected override void OnSessionChange(SessionChangeDescription changeDescription)
    {
        try
        {
            EventLog.WriteEntry($"Session change: {changeDescription.Reason} session {changeDescription.SessionId}", EventLogEntryType.Information);
        }
        catch { }

        // Trigger for attempts to launch into interactive session
        if (changeDescription.Reason == SessionChangeReason.SessionLogon ||
            changeDescription.Reason == SessionChangeReason.SessionUnlock ||
            changeDescription.Reason == SessionChangeReason.ConsoleConnect ||
            changeDescription.Reason == SessionChangeReason.RemoteConnect)
        {
            TryLaunchForSession((uint)changeDescription.SessionId);
        }
    }

    void TryLaunchInActiveConsoleSession()
    {
        uint sessionId = WTSGetActiveConsoleSessionId();
        if (sessionId != 0xFFFFFFFF)
        {
            TryLaunchForSession(sessionId);
        }
    }

    // --- New approach: duplicate SYSTEM token, set TokenSessionId, CreateProcessAsUserW ---
    void TryLaunchForSession(uint sessionId)
    {
        IntPtr systemToken = IntPtr.Zero;
        IntPtr primaryToken = IntPtr.Zero;
        IntPtr envBlock = IntPtr.Zero;

        // Adjust path as needed
        string appPath = @"C:\Exam\reporter.exe";
        string commandLine = $"\"{appPath}\"";

        try
        {
            // Avoid double-launch: check if reporter.exe already running in target session
            try
            {
                var running = Process.GetProcessesByName(System.IO.Path.GetFileNameWithoutExtension(appPath));
                if (running.Any(p => (uint)GetProcessSessionId((uint)p.Id) == sessionId))
                {
                    EventLog.WriteEntry($"Reporter already running in session {sessionId}; skipping launch.", EventLogEntryType.Information);
                    return;
                }
            }
            catch { /* non-fatal */ }

            // 1) open current process token (service runs as LocalSystem)
            if (!OpenProcessToken(GetCurrentProcess(), TOKEN_DUPLICATE | TOKEN_ASSIGN_PRIMARY | TOKEN_QUERY, out systemToken))
            {
                EventLog.WriteEntry($"OpenProcessToken failed. Err={Marshal.GetLastWin32Error()}", EventLogEntryType.Error);
                return;
            }

            // 2) duplicate to primary token
            SECURITY_ATTRIBUTES sa = new SECURITY_ATTRIBUTES();
            sa.nLength = Marshal.SizeOf(sa);
            if (!DuplicateTokenEx(systemToken, TOKEN_ALL_ACCESS, ref sa,
                (int)SECURITY_IMPERSONATION_LEVEL.SecurityImpersonation, (int)TOKEN_TYPE.TokenPrimary, out primaryToken))
            {
                EventLog.WriteEntry($"DuplicateTokenEx(system) failed. Err={Marshal.GetLastWin32Error()}", EventLogEntryType.Error);
                return;
            }

            // 3) set TokenSessionId on the primary token so the process shows in target session
            int sessionIdInt = (int)sessionId;
            IntPtr sessionIdPtr = Marshal.AllocHGlobal(Marshal.SizeOf(typeof(int)));
            try
            {
                Marshal.WriteInt32(sessionIdPtr, sessionIdInt);
                bool siOk = SetTokenInformation(primaryToken, TOKEN_INFORMATION_CLASS.TokenSessionId, sessionIdPtr, (uint)Marshal.SizeOf(typeof(int)));
                if (!siOk)
                {
                    EventLog.WriteEntry($"SetTokenInformation(TokenSessionId) failed. Err={Marshal.GetLastWin32Error()}", EventLogEntryType.Error);
                    return;
                }
            }
            finally
            {
                Marshal.FreeHGlobal(sessionIdPtr);
            }

            // 4) create environment block for new token (optional but helps)
            if (!CreateEnvironmentBlock(out envBlock, primaryToken, false))
            {
                EventLog.WriteEntry($"CreateEnvironmentBlock failed. Err={Marshal.GetLastWin32Error()}", EventLogEntryType.Warning);
                envBlock = IntPtr.Zero; // continue anyway
            }

            // 5) create the interactive process as SYSTEM in target session
            STARTUPINFOW si = new STARTUPINFOW();
            si.cb = Marshal.SizeOf(si);
            si.lpDesktop = "winsta0\\default";
            PROCESS_INFORMATION pi = new PROCESS_INFORMATION();

            uint creationFlags = CREATE_UNICODE_ENVIRONMENT | CREATE_NEW_CONSOLE;

            bool created = CreateProcessAsUserW(
                primaryToken,
                null,
                new StringBuilder(commandLine),
                ref sa,
                ref sa,
                false,
                creationFlags,
                envBlock,
                null,
                ref si,
                out pi
            );

            if (!created)
            {
                EventLog.WriteEntry($"CreateProcessAsUserW failed. Err={Marshal.GetLastWin32Error()}", EventLogEntryType.Error);
            }
            else
            {
                EventLog.WriteEntry($"Launched {appPath} as SYSTEM in session {sessionId} (PID {pi.dwProcessId}).", EventLogEntryType.Information);
                CloseHandle(pi.hProcess);
                CloseHandle(pi.hThread);
            }
        }
        finally
        {
            if (envBlock != IntPtr.Zero) DestroyEnvironmentBlock(envBlock);
            if (primaryToken != IntPtr.Zero) CloseHandle(primaryToken);
            if (systemToken != IntPtr.Zero) CloseHandle(systemToken);
        }
    }

    // Helper: get session id for a process (uses WTSQuerySessionInformation)
    static uint GetProcessSessionId(uint pid)
    {
        IntPtr hProcess = OpenProcessForQuery(pid);
        if (hProcess == IntPtr.Zero) return 0xFFFFFFFF;
        uint sessionId = 0xFFFFFFFF;
        if (!ProcessIdToSessionId(pid, out sessionId))
        {
            sessionId = 0xFFFFFFFF;
        }
        CloseHandle(hProcess);
        return sessionId;
    }

    // ---- P/Invoke / structs / enums ----

    [DllImport("wtsapi32.dll", SetLastError = true)]
    static extern bool WTSQueryUserToken(int sessionId, out IntPtr Token); // retained if needed elsewhere

    [DllImport("kernel32.dll")]
    static extern uint WTSGetActiveConsoleSessionId();

    [DllImport("advapi32.dll", SetLastError = true)]
    static extern bool DuplicateTokenEx(
        IntPtr hExistingToken,
        int dwDesiredAccess,
        ref SECURITY_ATTRIBUTES lpTokenAttributes,
        int ImpersonationLevel,
        int TokenType,
        out IntPtr phNewToken);

    [DllImport("userenv.dll", SetLastError = true)]
    static extern bool CreateEnvironmentBlock(out IntPtr lpEnvironment, IntPtr hToken, bool bInherit);

    [DllImport("userenv.dll", SetLastError = true)]
    static extern bool DestroyEnvironmentBlock(IntPtr lpEnvironment);

    [DllImport("advapi32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
    static extern bool CreateProcessAsUserW(
        IntPtr hToken,
        string lpApplicationName,
        StringBuilder lpCommandLine,
        ref SECURITY_ATTRIBUTES lpProcessAttributes,
        ref SECURITY_ATTRIBUTES lpThreadAttributes,
        bool bInheritHandles,
        uint dwCreationFlags,
        IntPtr lpEnvironment,
        string lpCurrentDirectory,
        ref STARTUPINFOW lpStartupInfo,
        out PROCESS_INFORMATION lpProcessInformation);

    [DllImport("advapi32.dll", SetLastError = true)]
    static extern bool OpenProcessToken(IntPtr ProcessHandle, int DesiredAccess, out IntPtr TokenHandle);

    [DllImport("kernel32.dll")]
    static extern IntPtr GetCurrentProcess();

    [DllImport("advapi32.dll", SetLastError = true)]
    static extern bool SetTokenInformation(IntPtr TokenHandle, TOKEN_INFORMATION_CLASS TokenInformationClass, IntPtr TokenInformation, uint TokenInformationLength);

    [DllImport("kernel32.dll", SetLastError = true)]
    static extern bool CloseHandle(IntPtr hObject);

    [DllImport("kernel32.dll")]
    static extern bool ProcessIdToSessionId(uint dwProcessId, out uint pSessionId);

    // We open process to get a handle for some queries
    [DllImport("kernel32.dll", SetLastError = true)]
    static extern IntPtr OpenProcess(uint processAccess, bool bInheritHandle, uint processId);

    static IntPtr OpenProcessForQuery(uint pid)
    {
        const uint PROCESS_QUERY_LIMITED_INFORMATION = 0x1000;
        return OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, false, pid);
    }

    [StructLayout(LayoutKind.Sequential)]
    struct PROCESS_INFORMATION
    {
        public IntPtr hProcess;
        public IntPtr hThread;
        public uint dwProcessId;
        public uint dwThreadId;
    }

    [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
    struct STARTUPINFOW
    {
        public int cb;
        public string lpReserved;
        public string lpDesktop;
        public string lpTitle;
        public uint dwX;
        public uint dwY;
        public uint dwXSize;
        public uint dwYSize;
        public uint dwXCountChars;
        public uint dwYCountChars;
        public uint dwFillAttribute;
        public uint dwFlags;
        public short wShowWindow;
        public short cbReserved2;
        public IntPtr lpReserved2;
        public IntPtr hStdInput;
        public IntPtr hStdOutput;
        public IntPtr hStdError;
    }

    [StructLayout(LayoutKind.Sequential)]
    struct SECURITY_ATTRIBUTES
    {
        public int nLength;
        public IntPtr lpSecurityDescriptor;
        public bool bInheritHandle;
    }

    enum TOKEN_TYPE { TokenPrimary = 1, TokenImpersonation = 2 }
    enum SECURITY_IMPERSONATION_LEVEL { SecurityAnonymous = 0, SecurityIdentification = 1, SecurityImpersonation = 2, SecurityDelegation = 3 }

    enum TOKEN_INFORMATION_CLASS {
        TokenUser = 1,
        TokenGroups,
        TokenPrivileges,
        TokenOwner,
        TokenPrimaryGroup,
        TokenDefaultDacl,
        TokenSource,
        TokenType,
        TokenImpersonationLevel,
        TokenStatistics,
        TokenRestrictedSids,
        TokenSessionId = 12
    }

    // simple service entry
    public static void Main()
    {
        ServiceBase.Run(new InteractiveLauncherService());
    }
}
