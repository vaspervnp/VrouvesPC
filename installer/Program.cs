using Avalonia;

namespace VrouvesSetup;

internal static class Program
{
    /// <summary>
    /// --uninstall: remove the game instead of installing it; --quiet: do it at once with no
    /// questions; --dir DIR: install there; --no-shortcuts: no desktop or menu shortcuts.
    /// </summary>
    [STAThread]
    public static void Main(string[] args)
    {
        App.Args = args;
        BuildAvaloniaApp().StartWithClassicDesktopLifetime(args);
    }

    public static AppBuilder BuildAvaloniaApp() =>
        AppBuilder.Configure<App>().UsePlatformDetect().WithInterFont().LogToTrace();
}
