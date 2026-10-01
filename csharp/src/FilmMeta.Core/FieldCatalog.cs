using System.Text.Json;

namespace FilmMeta.Core;

public sealed record FieldDefinition(
    string Id, string Role, string Field, string LabelKey,
    string XmpProperty, string? AnalogProperty, string? ExifTag,
    string[] StandardXmp, bool DefaultVisible);

public static class FieldCatalog
{
    public const string Namespace = "urn:filmmeta:metadata:1.0/";
    public const string Prefix = "Xmp.fm.";
    public const string AnalogNamespace = "http://analogexif.sourceforge.net/ns";
    public const string AnalogPrefix = "Xmp.AnalogExif.";

    public static IReadOnlyList<FieldDefinition> Fields { get; } = Load();

    private static IReadOnlyList<FieldDefinition> Load()
    {
        using var stream = typeof(FieldCatalog).Assembly.GetManifestResourceStream(
            "FilmMeta.Core.Resources.fields.json")
            ?? throw new InvalidOperationException("The field catalog is missing.");
        var fields = JsonSerializer.Deserialize<FieldDefinition[]>(stream,
            new JsonSerializerOptions(JsonSerializerDefaults.Web))
            ?? throw new InvalidOperationException("The field catalog is invalid.");
        if (fields.Length != 29 || fields.Select(x => x.Id).Distinct().Count() != fields.Length)
            throw new InvalidOperationException("The field catalog contains invalid identifiers.");
        return Array.AsReadOnly(fields);
    }
}
