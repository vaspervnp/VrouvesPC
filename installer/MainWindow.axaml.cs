using System.Globalization;
using Avalonia.Controls;
using Avalonia.Interactivity;
using Avalonia.Platform.Storage;
using Avalonia.Threading;

namespace VrouvesSetup;

public partial class MainWindow : Window
{
    enum Page { Welcome, Options, Work, Done }

    readonly Installer inst = new();
    readonly bool uninstallMode;
    readonly bool quiet;
    Page page = Page.Welcome;
    bool working;
    bool succeeded;
    string? error;
    int lang = CultureInfo.CurrentUICulture.TwoLetterISOLanguageName == "el" ? 1 : 0;

    // id -> English, Greek
    static readonly Dictionary<string, string[]> T = new()
    {
        ["lang"] = ["Ελληνικά", "English"],
        ["welcome"] = ["Welcome!", "Καλώς ήρθες!"],
        ["welcome_text"] = ["This will install Let's Go For Vrouves, the cute tower defence where the villagers of Zoniana save their bitter greens from Frankenstein & Moreau Co.\n\nIt installs for you only, so it needs no administrator rights.",
            "Θα εγκατασταθεί το «Πάμε για Βρούβες», το χαριτωμένο tower defence όπου οι χωριανοί των Ζωνιανών σώζουν τα πικρά τους χόρτα από την Frankenstein & Moreau Co.\n\nΕγκαθίσταται μόνο για σένα, χωρίς δικαιώματα διαχειριστή."],
        ["existing"] = ["The game is already installed in {0}. Next installs it again over it.", "Το παιχνίδι είναι ήδη εγκατεστημένο στο {0}. Το «Επόμενο» το εγκαθιστά ξανά από πάνω."],
        ["uninstall_btn"] = ["Uninstall it", "Απεγκατάσταση"],
        ["no_payload"] = ["This setup was built without the game inside it.", "Αυτό το setup φτιάχτηκε χωρίς το παιχνίδι μέσα."],
        ["options"] = ["Where shall the vrouves grow?", "Πού θα φυτρώσουν οι βρούβες;"],
        ["folder"] = ["Install folder:", "Φάκελος εγκατάστασης:"],
        ["browse"] = ["Browse...", "Αναζήτηση..."],
        ["desktop"] = ["Shortcut on the desktop", "Συντόμευση στην επιφάνεια εργασίας"],
        ["menu"] = ["Shortcut in the Start menu / applications", "Συντόμευση στο μενού εφαρμογών"],
        ["space"] = ["Needs about {0} MB of disk space.", "Χρειάζεται περίπου {0} MB στο δίσκο."],
        ["installing"] = ["Planting the vrouves...", "Φυτεύουμε τις βρούβες..."],
        ["removing"] = ["Picking the vrouves...", "Μαζεύουμε τις βρούβες..."],
        ["unpack"] = ["Unpacking the game", "Αποσυμπίεση του παιχνιδιού"],
        ["shortcuts"] = ["Making the shortcuts", "Δημιουργία συντομεύσεων"],
        ["remove"] = ["Removing the game", "Αφαίρεση του παιχνιδιού"],
        ["done"] = ["Done!", "Έτοιμο!"],
        ["removed"] = ["Removed", "Αφαιρέθηκε"],
        ["done_title"] = ["The village is ready!", "Το χωριό είναι έτοιμο!"],
        ["done_text"] = ["Let's Go For Vrouves is installed in {0}.\nKali orexi!", "Το «Πάμε για Βρούβες» εγκαταστάθηκε στο {0}.\nΚαλή όρεξη!"],
        ["removed_title"] = ["Uninstalled", "Απεγκαταστάθηκε"],
        ["removed_text"] = ["The game has been removed. Your high scores stay, in case you come back.", "Το παιχνίδι αφαιρέθηκε. Τα ρεκόρ σου μένουν, για όταν ξαναέρθεις."],
        ["failed"] = ["Something went wrong", "Κάτι πήγε στραβά"],
        ["launch"] = ["Play now", "Παίξε τώρα"],
        ["uninstall_title"] = ["Uninstall Let's Go For Vrouves?", "Απεγκατάσταση του «Πάμε για Βρούβες»;"],
        ["uninstall_text"] = ["This removes the game from {0}, with its shortcuts.", "Αφαιρείται το παιχνίδι από το {0}, μαζί με τις συντομεύσεις."],
        ["next"] = ["Next", "Επόμενο"],
        ["install"] = ["Install", "Εγκατάσταση"],
        ["uninstall"] = ["Uninstall", "Απεγκατάσταση"],
        ["finish"] = ["Finish", "Τέλος"],
        ["back"] = ["Back", "Πίσω"],
        ["cancel"] = ["Cancel", "Άκυρο"],
    };

    string S(string id) => T[id][lang];

    public MainWindow() : this([]) { }

    public MainWindow(string[] args)
    {
        InitializeComponent();
        uninstallMode = args.Contains("--uninstall");
        quiet = args.Contains("--quiet");
        var existing = Installer.Existing();
        if (existing != null)
        {
            inst.Dir = existing.Dir;
            inst.DesktopShortcut = existing.DesktopShortcut;
            inst.MenuShortcut = existing.MenuShortcut;
        }
        int d = Array.IndexOf(args, "--dir");
        if (d >= 0 && d + 1 < args.Length)
            inst.Dir = args[d + 1];
        if (args.Contains("--no-shortcuts"))
            inst.DesktopShortcut = inst.MenuShortcut = false;
        FolderBox.Text = inst.Dir;
        DesktopCheck.IsChecked = inst.DesktopShortcut;
        MenuCheck.IsChecked = inst.MenuShortcut;
        Closing += (_, e) => e.Cancel = working;
        Refresh();
        // --quiet: install (or uninstall) straight away with the defaults, then close
        if (quiet)
            Dispatcher.UIThread.Post(() => _ = RunAsync());
    }

    void Refresh()
    {
        LangButton.Content = S("lang");
        CancelButton.Content = S("cancel");
        BackButton.Content = S("back");
        PageWelcome.IsVisible = page == Page.Welcome;
        PageOptions.IsVisible = page == Page.Options;
        PageWork.IsVisible = page == Page.Work;
        PageDone.IsVisible = page == Page.Done;
        BackButton.IsVisible = page == Page.Options;
        CancelButton.IsVisible = page is Page.Welcome or Page.Options;
        NextButton.IsEnabled = !working;

        if (uninstallMode)
        {
            WelcomeTitle.Text = S("uninstall_title");
            WelcomeText.Text = string.Format(S("uninstall_text"), inst.Dir);
            NextButton.Content = page == Page.Done ? S("finish") : S("uninstall");
        }
        else
        {
            WelcomeTitle.Text = S("welcome");
            WelcomeText.Text = Installer.HasPayload ? S("welcome_text") : S("no_payload");
            var existing = Installer.Existing();
            ExistingText.IsVisible = UninstallButton.IsVisible = existing != null && page == Page.Welcome;
            if (existing != null)
                ExistingText.Text = string.Format(S("existing"), existing.Dir);
            UninstallButton.Content = S("uninstall_btn");
            NextButton.Content = page switch
            {
                Page.Options => S("install"),
                Page.Done => S("finish"),
                _ => S("next"),
            };
            NextButton.IsEnabled = !working && Installer.HasPayload;
        }
        OptionsTitle.Text = S("options");
        FolderLabel.Text = S("folder");
        BrowseButton.Content = S("browse");
        DesktopCheck.Content = S("desktop");
        MenuCheck.Content = S("menu");
        SpaceText.Text = string.Format(S("space"), OperatingSystem.IsMacOS() ? 190 : OperatingSystem.IsWindows() ? 130 : 95);
        WorkTitle.Text = uninstallMode ? S("removing") : S("installing");
        LaunchCheck.Content = S("launch");
        LaunchCheck.IsVisible = !uninstallMode && succeeded;
        if (page == Page.Done)
        {
            if (error != null)
            {
                DoneTitle.Text = S("failed");
                DoneText.Text = error;
            }
            else if (uninstallMode)
            {
                DoneTitle.Text = S("removed_title");
                DoneText.Text = S("removed_text");
            }
            else
            {
                DoneTitle.Text = S("done_title");
                DoneText.Text = string.Format(S("done_text"), inst.Dir);
            }
        }
    }

    void OnLang(object? sender, RoutedEventArgs e)
    {
        lang = 1 - lang;
        Refresh();
    }

    void OnCancel(object? sender, RoutedEventArgs e) => Close();

    void OnBack(object? sender, RoutedEventArgs e)
    {
        page = Page.Welcome;
        Refresh();
    }

    void OnUninstallExisting(object? sender, RoutedEventArgs e)
    {
        var existing = Installer.Existing();
        if (existing == null)
            return;
        // the uninstaller next to the game does it, so this setup can stay put
        page = Page.Work;
        _ = RunUninstallFromSetup(existing);
    }

    async Task RunUninstallFromSetup(Installer existing)
    {
        working = true;
        Refresh();
        WorkTitle.Text = S("removing");
        try
        {
            await existing.UninstallAsync(new Progress<(double, string)>(Report));
            error = null;
        }
        catch (Exception ex)
        {
            error = ex.Message;
        }
        working = false;
        page = Page.Welcome;
        Refresh();
    }

    async void OnBrowse(object? sender, RoutedEventArgs e)
    {
        var picked = await StorageProvider.OpenFolderPickerAsync(new FolderPickerOpenOptions { AllowMultiple = false });
        if (picked.Count > 0 && picked[0].TryGetLocalPath() is { } p)
            FolderBox.Text = OperatingSystem.IsMacOS() ? p : Path.Combine(p, Installer.Id);
    }

    async void OnNext(object? sender, RoutedEventArgs e)
    {
        switch (page)
        {
            case Page.Welcome when uninstallMode:
                await RunAsync();
                break;
            case Page.Welcome:
                page = Page.Options;
                Refresh();
                break;
            case Page.Options:
                inst.Dir = (FolderBox.Text ?? "").Trim();
                inst.DesktopShortcut = DesktopCheck.IsChecked == true;
                inst.MenuShortcut = MenuCheck.IsChecked == true;
                await RunAsync();
                break;
            case Page.Done:
                if (succeeded && !uninstallMode && LaunchCheck.IsChecked == true)
                    inst.Launch();
                Close();
                break;
        }
    }

    void Report((double v, string what) p)
    {
        Progress.Value = p.v;
        WorkText.Text = S(p.what);
    }

    async Task RunAsync()
    {
        page = Page.Work;
        working = true;
        Refresh();
        try
        {
            var prog = new Progress<(double, string)>(Report);
            if (uninstallMode)
                await inst.UninstallAsync(prog);
            else
                await inst.InstallAsync(prog);
            succeeded = true;
        }
        catch (Exception ex)
        {
            error = ex.Message;
        }
        working = false;
        page = Page.Done;
        Refresh();
        if (quiet)
        {
            if (error != null)
                Console.Error.WriteLine(error);
            Close();
        }
    }
}
