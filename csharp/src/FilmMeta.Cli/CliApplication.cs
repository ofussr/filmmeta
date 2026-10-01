using System.Reflection;
using System.Text.Encodings.Web;
using System.Text.Json;
using FilmMeta.Core;
using FilmMeta.Metadata;

namespace FilmMeta.Cli;

public sealed record ReadFailure(string Path, string Error);
public sealed record ReadReport(int SchemaVersion, string Version, IReadOnlyList<MetadataSnapshot> Files,
    IReadOnlyList<ReadFailure> Errors, bool Cancelled);

public sealed class CliApplication(IMetadataReader reader)
{
    private static readonly JsonSerializerOptions JsonOptions = new(JsonSerializerDefaults.Web)
    {
        WriteIndented = true,
        Encoder = JavaScriptEncoder.UnsafeRelaxedJsonEscaping
    };

    public static string Version => typeof(CliApplication).Assembly
        .GetCustomAttribute<AssemblyInformationalVersionAttribute>()?.InformationalVersion.Split('+')[0]
        ?? "unknown";

    public int Run(string[] args, TextWriter output, TextWriter error, CancellationToken cancellationToken = default)
    {
        if (args.Length == 0 || args[0] is "help" or "--help" or "-h")
        {
            output.WriteLine("FilmMeta C# read prototype");
            output.WriteLine("  FilmMeta.Cli read <file-or-folder> [...] [--recursive] [--json]");
            output.WriteLine("  FilmMeta.Cli fields");
            output.WriteLine("  FilmMeta.Cli --version");
            output.WriteLine("Supported: JPG, JPEG, TIF, TIFF, DNG. Photos are opened read-only.");
            return 0;
        }
        if (args[0] == "--version" && args.Length == 1)
        {
            output.WriteLine(Version);
            return 0;
        }
        if (args[0] == "fields" && args.Length == 1)
        {
            output.WriteLine(JsonSerializer.Serialize(FieldCatalog.Fields, JsonOptions));
            return 0;
        }
        if (args[0] != "read")
            return Usage("Unknown command: " + args[0]);

        var json = false;
        var recursive = false;
        var literal = false;
        var inputs = new List<string>();
        foreach (var arg in args.Skip(1))
        {
            if (!literal && arg == "--") { literal = true; continue; }
            if (!literal && arg == "--json") { json = true; continue; }
            if (!literal && arg == "--recursive") { recursive = true; continue; }
            if (!literal && arg.StartsWith('-'))
                return Usage("Unknown option: " + arg);
            inputs.Add(arg);
        }
        if (inputs.Count == 0)
            return Usage("Specify at least one image or folder.");

        var files = new List<MetadataSnapshot>();
        var failures = new List<ReadFailure>();
        var seen = new HashSet<string>(OperatingSystem.IsWindows() ? StringComparer.OrdinalIgnoreCase : StringComparer.Ordinal);
        var cancelled = false;
        try
        {
            foreach (var input in inputs)
            {
                cancellationToken.ThrowIfCancellationRequested();
                try
                {
                    var paths = System.IO.Directory.Exists(input)
                        ? System.IO.Directory.EnumerateFiles(input, "*", new EnumerationOptions
                        {
                            RecurseSubdirectories = recursive,
                            AttributesToSkip = FileAttributes.ReparsePoint,
                            IgnoreInaccessible = false
                        }).Where(PhotoMetadataReader.IsSupportedPath)
                        : new[] { input };
                    var found = false;
                    foreach (var path in paths)
                    {
                        cancellationToken.ThrowIfCancellationRequested();
                        found = true;
                        var fullPath = Path.GetFullPath(path);
                        if (!seen.Add(fullPath))
                            continue;
                        try
                        {
                            var snapshot = reader.Read(fullPath, cancellationToken);
                            files.Add(snapshot);
                            if (!json)
                                Print(snapshot, output);
                        }
                        catch (Exception e) when (IsFileError(e))
                        {
                            failures.Add(new ReadFailure(fullPath, e.Message));
                        }
                    }
                    if (!found)
                        failures.Add(new ReadFailure(input, "No supported images found in the folder."));
                }
                catch (Exception e) when (IsFileError(e))
                {
                    failures.Add(new ReadFailure(input, e.Message));
                }
            }
        }
        catch (OperationCanceledException)
        {
            cancelled = true;
        }

        if (json)
            output.WriteLine(JsonSerializer.Serialize(new ReadReport(1, Version, files, failures, cancelled), JsonOptions));
        else
        {
            foreach (var failure in failures)
                error.WriteLine(failure.Path + ": " + failure.Error);
            error.WriteLine($"Read: {files.Count}; errors: {failures.Count}" + (cancelled ? "; cancelled" : ""));
        }
        return cancelled ? 130 : failures.Count != 0 ? 1 : 0;

        int Usage(string message)
        {
            error.WriteLine(message);
            error.WriteLine("Use --help for usage.");
            return 2;
        }
    }

    private static bool IsFileError(Exception e) =>
        e is IOException or InvalidDataException or UnauthorizedAccessException or NotSupportedException
            or ArgumentException or MetadataExtractor.ImageProcessingException;

    private static void Print(MetadataSnapshot snapshot, TextWriter output)
    {
        output.WriteLine(snapshot.Path + " [" + snapshot.Format + "]");
        foreach (var (id, value) in snapshot.Values.Where(x => x.Value.Length != 0))
            output.WriteLine($"  {id} = {value}" + (snapshot.Sources[id].Length != 0 ? $" [{snapshot.Sources[id]}]" : ""));
        foreach (var warning in snapshot.Warnings)
            output.WriteLine("  Warning: " + warning);
        output.WriteLine();
    }
}
