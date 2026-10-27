using System.Diagnostics;
using System.IO.Compression;
using System.Reflection;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace VrouvesSetup;

/// <summary>
/// Installs the game for the current user, with no administrator rights:
/// Windows  %LOCALAPPDATA%\Programs\LetsGoForVrouves, Start menu and desktop shortcuts, and an
///          entry in Settings > Apps (HKCU) that runs the uninstaller;
/// Linux    ~/.local/share/LetsGoForVrouves, a .desktop entry in the applications menu and
///          on the desktop, the icon in the hicolor theme;
/// macOS    ~/Applications/Let's Go For Vrouves.app, and an alias on the desktop.
/// The uninstaller is a copy of this program, kept next to the game.
/// </summary>
public sealed class Installer
{
    public const string AppName = "Let's Go For Vrouves";
    public const string Id = "LetsGoForVrouves";
    public const string Version = "1.0.0";
    const string GameWin = "LetsGoForVrouves.exe";
    const string GameLinux = "LetsGoForVrouves.x86_64";
    const string MacApp = "Let's Go For Vrouves.app";
    const string Marker = "install.json";

    public string Dir { get; set; } = DefaultDir();
    public bool DesktopShortcut { get; set; } = true;
    public bool MenuShortcut { get; set; } = true;

    static string Home => Environment.GetFolderPath(Environment.SpecialFolder.UserProfile);

    public static string DefaultDir()
    {
        if (OperatingSystem.IsWindows())
            return Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "Programs", Id);
        if (OperatingSystem.IsMacOS())
            return Path.Combine(Home, "Applications");
        return Path.Combine(Home, ".local", "share", Id);
    }

    public string GamePath => OperatingSystem.IsWindows() ? Path.Combine(Dir, GameWin)
        : OperatingSystem.IsMacOS() ? Path.Combine(Dir, MacApp) : Path.Combine(Dir, GameLinux);

    /// <summary>where the uninstaller and the record of what was installed live</summary>
    string DataDir => OperatingSystem.IsMacOS()
        ? Path.Combine(Home, "Library", "Application Support", Id) : Dir;

    public static bool HasPayload => Assembly.GetExecutingAssembly().GetManifestResourceInfo("payload.zip") != null;

    /// <summary>
    /// the installed copy, if any, from its record: next to this program first (it is the
    /// uninstaller of a copy installed anywhere), then in the default place
    /// </summary>
    public static Installer? Existing()
    {
        var here = Path.GetDirectoryName(Environment.ProcessPath ?? "") ?? "";
        var marker = Path.Combine(here, Marker);
        if (!File.Exists(marker))
            marker = Path.Combine(new Installer().DataDir, Marker);
        if (!File.Exists(marker))
            return null;
        try
        {
            var rec = JsonSerializer.Deserialize(File.ReadAllText(marker), RecordJson.Default.Record);
            if (rec == null)
                return null;
            return new Installer { Dir = rec.Dir, DesktopShortcut = rec.Desktop, MenuShortcut = rec.Menu };
        }
        catch (Exception)
        {
            return null;
        }
    }

    public record Record(string Dir, bool Desktop, bool Menu, string Version, List<string> Files);

    // ================================================================== install

    public async Task InstallAsync(IProgress<(double, string)> progress)
    {
        await Task.Run(() =>
        {
            Directory.CreateDirectory(Dir);
            Directory.CreateDirectory(DataDir);
            var files = new List<string>();
            progress.Report((0.02, "unpack"));
            using (var s = Assembly.GetExecutingAssembly().GetManifestResourceStream("payload.zip")
                         ?? throw new InvalidOperationException("This setup has no game inside it."))
            using (var zip = new ZipArchive(s, ZipArchiveMode.Read))
            {
                long total = Math.Max(1, zip.Entries.Sum(e => e.Length));
                long done = 0;
                foreach (var e in zip.Entries)
                {
                    var dest = Path.GetFullPath(Path.Combine(Dir, e.FullName));
                    if (!dest.StartsWith(Path.GetFullPath(Dir), StringComparison.Ordinal))
                        continue;   // never write outside the install folder
                    if (e.FullName.EndsWith('/'))
                    {
                        Directory.CreateDirectory(dest);
                        continue;
                    }
                    Directory.CreateDirectory(Path.GetDirectoryName(dest)!);
                    using (var src = e.Open())
                    using (var dst = File.Create(dest))
                    {
                        var buf = new byte[1 << 20];
                        int n;
                        while ((n = src.Read(buf, 0, buf.Length)) > 0)
                        {
                            dst.Write(buf, 0, n);
                            done += n;
                            progress.Report((0.05 + 0.8 * done / total, "unpack"));
                        }
                    }
                    files.Add(dest);
                }
            }
            progress.Report((0.88, "shortcuts"));
            MakeExecutable();
            CopyUninstaller();
            if (OperatingSystem.IsWindows())
                WindowsShortcuts();
            else if (OperatingSystem.IsMacOS())
                MacShortcuts();
            else
                LinuxShortcuts();
            var rec = new Record(Dir, DesktopShortcut, MenuShortcut, Version, files);
            File.WriteAllText(Path.Combine(DataDir, Marker), JsonSerializer.Serialize(rec, RecordJson.Default.Record));
            progress.Report((1.0, "done"));
        });
    }

    void MakeExecutable()
    {
        if (OperatingSystem.IsWindows())
            return;
        if (OperatingSystem.IsMacOS())
        {
            var bin = Path.Combine(GamePath, "Contents", "MacOS");
            if (Directory.Exists(bin))
                foreach (var f in Directory.GetFiles(bin))
                    Chmod(f);
            // a downloaded app is quarantined; this one was put there by the user's own setup
            Run("xattr", "-dr", "com.apple.quarantine", GamePath);
        }
        else
            Chmod(GamePath);
    }

    static void Chmod(string f)
    {
        if (!OperatingSystem.IsWindows())
            File.SetUnixFileMode(f, File.GetUnixFileMode(f) | UnixFileMode.UserExecute | UnixFileMode.GroupExecute | UnixFileMode.OtherExecute);
    }

    string UninstallerPath => Path.Combine(DataDir, OperatingSystem.IsWindows() ? "uninstall.exe" : "uninstall");

    void CopyUninstaller()
    {
        var self = Environment.ProcessPath;
        if (self == null || Path.GetFullPath(self) == Path.GetFullPath(UninstallerPath))
            return;
        using (var un = Assembly.GetExecutingAssembly().GetManifestResourceStream("uninstall.bin"))
        {
            if (un != null)
            {
                using var f = File.Create(UninstallerPath);
                un.CopyTo(f);
            }
            else
                File.Copy(self, UninstallerPath, true);
        }
        Chmod(UninstallerPath);
        if (OperatingSystem.IsWindows())
            File.WriteAllBytes(Path.Combine(Dir, "icon.ico"), ReadAsset("icon.ico"));
        else
            File.WriteAllBytes(Path.Combine(DataDir, "icon.png"), ReadAsset("icon.png"));
    }

    static byte[] ReadAsset(string name)
    {
        using var s = Avalonia.Platform.AssetLoader.Open(new Uri("avares://VrouvesSetup/Assets/" + name));
        using var m = new MemoryStream();
        s.CopyTo(m);
        return m.ToArray();
    }

    // ------------------------------------------------------------------ Windows

    static string StartMenuDir => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.Programs));
    static string DesktopDir => Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);

    void WindowsShortcuts()
    {
        if (!OperatingSystem.IsWindows())
            return;
        if (MenuShortcut)
            Lnk(Path.Combine(StartMenuDir, AppName + ".lnk"));
        if (DesktopShortcut)
            Lnk(Path.Combine(DesktopDir, AppName + ".lnk"));
        using var k = Microsoft.Win32.Registry.CurrentUser.CreateSubKey(
            @"Software\Microsoft\Windows\CurrentVersion\Uninstall\" + Id);
        k.SetValue("DisplayName", AppName);
        k.SetValue("DisplayVersion", Version);
        k.SetValue("Publisher", "Revive8bit");
        k.SetValue("DisplayIcon", GamePath);
        k.SetValue("InstallLocation", Dir);
        k.SetValue("UninstallString", $"\"{UninstallerPath}\" --uninstall");
        k.SetValue("QuietUninstallString", $"\"{UninstallerPath}\" --uninstall --quiet");
        k.SetValue("NoModify", 1);
        k.SetValue("NoRepair", 1);
        k.SetValue("EstimatedSize", (int)(new FileInfo(GamePath).Length / 1024));
    }

    void Lnk(string path)
    {
        // a .lnk through the shell's own scripting object, from PowerShell
        string Q(string s) => s.Replace("'", "''");
        var ps = $"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{Q(path)}');" +
                 $"$s.TargetPath='{Q(GamePath)}';$s.WorkingDirectory='{Q(Dir)}';" +
                 $"$s.IconLocation='{Q(GamePath)},0';$s.Description='{Q(AppName)}';$s.Save()";
        Run("powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-Command", ps);
    }

    // ------------------------------------------------------------------ Linux

    static string AppsDir => Path.Combine(Home, ".local", "share", "applications");
    static string IconFile => Path.Combine(Home, ".local", "share", "icons", "hicolor", "256x256", "apps", "letsgoforvrouves.png");

    static string LinuxDesktopDir()
    {
        // the desktop folder of the user's language, as xdg-user-dirs knows it
        var cfg = Path.Combine(Home, ".config", "user-dirs.dirs");
        if (File.Exists(cfg))
            foreach (var line in File.ReadAllLines(cfg))
                if (line.StartsWith("XDG_DESKTOP_DIR="))
                    return line["XDG_DESKTOP_DIR=".Length..].Trim('"').Replace("$HOME", Home);
        return Path.Combine(Home, "Desktop");
    }

    string DesktopEntry() =>
        "[Desktop Entry]\nType=Application\nName=" + AppName + "\nName[el]=Πάμε για Βρούβες\n" +
        "Comment=A cute tower defence: save the vrouves of Crete!\nComment[el]=Σώστε τις βρούβες της Κρήτης!\n" +
        $"Exec=\"{GamePath}\"\nPath={Dir}\nIcon=letsgoforvrouves\nTerminal=false\nCategories=Game;StrategyGame;\n";

    void LinuxShortcuts()
    {
        Directory.CreateDirectory(Path.GetDirectoryName(IconFile)!);
        File.WriteAllBytes(IconFile, ReadAsset("icon.png"));
        if (MenuShortcut)
        {
            Directory.CreateDirectory(AppsDir);
            File.WriteAllText(Path.Combine(AppsDir, "letsgoforvrouves.desktop"), DesktopEntry());
        }
        if (DesktopShortcut)
        {
            var d = LinuxDesktopDir();
            if (Directory.Exists(d))
            {
                var f = Path.Combine(d, "letsgoforvrouves.desktop");
                File.WriteAllText(f, DesktopEntry());
                Chmod(f);
                Run("gio", "set", f, "metadata::trusted", "true");
            }
        }
    }

    // ------------------------------------------------------------------ macOS

    void MacShortcuts()
    {
        if (DesktopShortcut)
        {
            var link = Path.Combine(Home, "Desktop", AppName);
            if (!File.Exists(link) && !Directory.Exists(link))
                File.CreateSymbolicLink(link, GamePath);
        }
    }

    // ================================================================== uninstall

    public async Task UninstallAsync(IProgress<(double, string)> progress)
    {
        await Task.Run(() =>
        {
            progress.Report((0.1, "remove"));
            Record? rec = null;
            var marker = Path.Combine(DataDir, Marker);
            if (File.Exists(marker))
                rec = JsonSerializer.Deserialize(File.ReadAllText(marker), RecordJson.Default.Record);
            if (OperatingSystem.IsWindows())
            {
                TryDelete(Path.Combine(StartMenuDir, AppName + ".lnk"));
                TryDelete(Path.Combine(DesktopDir, AppName + ".lnk"));
                Microsoft.Win32.Registry.CurrentUser.DeleteSubKeyTree(
                    @"Software\Microsoft\Windows\CurrentVersion\Uninstall\" + Id, false);
            }
            else if (OperatingSystem.IsMacOS())
            {
                TryDelete(Path.Combine(Home, "Desktop", AppName));
                if (Directory.Exists(GamePath))
                    Directory.Delete(GamePath, true);
            }
            else
            {
                TryDelete(Path.Combine(AppsDir, "letsgoforvrouves.desktop"));
                TryDelete(Path.Combine(LinuxDesktopDir(), "letsgoforvrouves.desktop"));
                TryDelete(IconFile);
            }
            progress.Report((0.5, "remove"));
            // only what setup put there; anything else in the folder is left alone
            if (rec != null)
                foreach (var f in rec.Files)
                    TryDelete(f);
            TryDelete(Path.Combine(Dir, "icon.ico"));
            TryDelete(Path.Combine(DataDir, "icon.png"));
            TryDelete(marker);
            progress.Report((0.9, "remove"));
            RemoveSelfAndFolder();
            progress.Report((1.0, "removed"));
        });
    }

    /// <summary>
    /// The uninstaller cannot delete itself while it runs: on Windows a short cmd waits for it
    /// to exit, then deletes it and the folder if empty; on Unix a running file can be unlinked.
    /// </summary>
    void RemoveSelfAndFolder()
    {
        var self = Environment.ProcessPath ?? "";
        bool selfInside = Path.GetFullPath(self) == Path.GetFullPath(UninstallerPath);
        if (OperatingSystem.IsWindows())
        {
            if (selfInside)
            {
                var cmd = $"/c ping 127.0.0.1 -n 3 > nul & del /f /q \"{UninstallerPath}\" & rmdir \"{Dir}\"";
                Process.Start(new ProcessStartInfo("cmd.exe", cmd) { CreateNoWindow = true, UseShellExecute = false });
                return;
            }
            TryDelete(UninstallerPath);
        }
        else
            TryDelete(UninstallerPath);
        TryRemoveDir(DataDir);
        if (!OperatingSystem.IsMacOS())
            TryRemoveDir(Dir);
    }

    static void TryDelete(string f)
    {
        try
        {
            if (File.Exists(f) || new FileInfo(f).LinkTarget != null)
                File.Delete(f);
        }
        catch (Exception) { }
    }

    static void TryRemoveDir(string d)
    {
        try
        {
            if (Directory.Exists(d) && !Directory.EnumerateFileSystemEntries(d).Any())
                Directory.Delete(d);
        }
        catch (Exception) { }
    }

    // ================================================================== running things

    public void Launch()
    {
        if (OperatingSystem.IsMacOS())
            Run("open", GamePath);
        else
            Process.Start(new ProcessStartInfo(GamePath) { WorkingDirectory = Dir, UseShellExecute = false });
    }

    static void Run(string exe, params string[] args)
    {
        try
        {
            var psi = new ProcessStartInfo(exe) { CreateNoWindow = true, UseShellExecute = false };
            foreach (var a in args)
                psi.ArgumentList.Add(a);
            using var p = Process.Start(psi);
            p?.WaitForExit(15000);
        }
        catch (Exception) { }
    }
}

/// <summary>the install record, read and written without reflection (the setup is trimmed)</summary>
[JsonSerializable(typeof(Installer.Record))]
internal partial class RecordJson : JsonSerializerContext;
