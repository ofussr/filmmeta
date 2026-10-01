using System.Collections.ObjectModel;

namespace FilmMeta.Core;

/// <summary>Field precedence and DNG routing, independent of a parser or user interface.</summary>
public static class MetadataResolver
{
    public static MetadataSnapshot Resolve(RawMetadata raw)
    {
        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        var sources = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var field in FieldCatalog.Fields)
        {
            var (value, source) = Custom(raw, field);
            if (value.Length == 0 && field.ExifTag is not null && !raw.IsDng)
                (value, source) = Standard(raw, field);
            values[field.Id] = value;
            sources[field.Id] = source;
        }

        foreach (var id in new[] { "film.name", "scanner.model" })
        {
            if (!sources[id].StartsWith(FieldCatalog.AnalogPrefix, StringComparison.Ordinal))
                continue;
            var role = id[..id.IndexOf('.')];
            var makerField = FieldCatalog.Fields.Single(x => x.Id == role + ".manufacturer");
            var analogMaker = Value(raw.Xmp, FieldCatalog.AnalogPrefix + makerField.AnalogProperty);
            var maker = analogMaker.Length != 0 ? analogMaker : Custom(raw, makerField).Value;
            values[id] = ShortName(values[id], maker);
        }

        var method = Value(raw.Xmp, FieldCatalog.Prefix + "DigitizationType");
        if (method is not ("scan" or "camera"))
        {
            method = new[] { "scanner.manufacturer", "scanner.model" }
                .Any(id => sources[id].StartsWith(FieldCatalog.AnalogPrefix, StringComparison.Ordinal))
                ? "scan" : "";
        }
        values["method"] = method;
        sources["method"] = Value(raw.Xmp, FieldCatalog.Prefix + "DigitizationType") == method
            && method.Length != 0 ? FieldCatalog.Prefix + "DigitizationType" : "";

        if (raw.IsDng && method == "camera")
        {
            FillDigitizer("copy_camera", "camera");
            FillDigitizer("copy_lens", "lens");
        }
        else if (raw.IsDng && method == "scan")
        {
            FillDigitizer("scanner", "camera");
        }

        return new MetadataSnapshot(raw.Path, raw.Format, raw.IsDng,
            new ReadOnlyDictionary<string, string>(values),
            new ReadOnlyDictionary<string, string>(sources),
            raw.Exif, raw.Xmp, raw.Warnings);

        void FillDigitizer(string target, string original)
        {
            foreach (var field in FieldCatalog.Fields.Where(x => x.Role == target))
            {
                if (values[field.Id].Length != 0)
                    continue;
                var originalField = FieldCatalog.Fields.FirstOrDefault(
                    x => x.Id == original + "." + field.Field);
                if (originalField?.ExifTag is null)
                    continue;
                (values[field.Id], sources[field.Id]) = Standard(raw, originalField);
            }
        }
    }

    private static (string Value, string Source) Custom(RawMetadata raw, FieldDefinition field)
    {
        var tag = FieldCatalog.Prefix + field.XmpProperty;
        var value = Value(raw.Xmp, tag);
        if (value.Length != 0)
            return (value, tag);
        if (field.AnalogProperty is not null)
        {
            tag = FieldCatalog.AnalogPrefix + field.AnalogProperty;
            value = Value(raw.Xmp, tag);
            if (value.Length != 0)
                return (value, tag);
        }
        return ("", "");
    }

    private static (string Value, string Source) Standard(RawMetadata raw, FieldDefinition field)
    {
        var exifTags = field.Id == "film.iso"
            ? new[] { field.ExifTag!, "Exif.Photo.RecommendedExposureIndex", "Exif.Photo.ISOSpeed" }
            : new[] { field.ExifTag! };
        foreach (var tag in exifTags)
        {
            var value = Value(raw.Exif, tag);
            if (value.Length != 0)
                return (value, tag);
        }
        foreach (var tag in field.StandardXmp)
        {
            var value = Value(raw.Xmp, tag);
            if (value.Length != 0)
                return (value, tag);
        }
        return ("", "");
    }

    private static string Value(IReadOnlyDictionary<string, string> data, string key) =>
        data.TryGetValue(key, out var value) ? value.Trim() : "";

    private static string ShortName(string name, string maker) =>
        maker.Length != 0 && name.StartsWith(maker + " ", StringComparison.OrdinalIgnoreCase)
            ? name[maker.Length..].Trim() : name;
}
