using System.Collections.ObjectModel;
using System.Globalization;
using FilmMeta.Core;
using MetadataExtractor;
using MetadataExtractor.Formats.Exif;
using MetadataExtractor.Formats.Xmp;
using XmpCore;

namespace FilmMeta.Metadata;

/// <summary>Read-only adapter. It never opens a photo with write access.</summary>
public sealed class PhotoMetadataReader : IMetadataReader
{
    public const long ReadLimit = 2_000_000_000;
    private const int DngVersionTag = 50706;

    public static bool IsSupportedPath(string path) => Path.GetExtension(path).ToLowerInvariant()
        is ".jpg" or ".jpeg" or ".tif" or ".tiff" or ".dng";

    public MetadataSnapshot Read(string path, CancellationToken cancellationToken = default)
    {
        cancellationToken.ThrowIfCancellationRequested();
        path = Path.GetFullPath(path);
        if (!IsSupportedPath(path))
            throw new NotSupportedException("Supported file extensions: JPG, JPEG, TIF, TIFF, DNG.");
        using var stream = new FileStream(path, FileMode.Open, FileAccess.Read, FileShare.Read);
        if (stream.Length >= ReadLimit)
            throw new NotSupportedException("Files of 2 GB or larger are outside the current read limit.");
        Span<byte> header = stackalloc byte[8];
        var count = stream.Read(header);
        if (count < 4)
            throw new InvalidDataException("The image header is incomplete.");
        var jpeg = header[0] == 0xff && header[1] == 0xd8 && header[2] == 0xff;
        var little = header[0] == 'I' && header[1] == 'I';
        var big = header[0] == 'M' && header[1] == 'M';
        if ((little && header[2] == 43 && header[3] == 0)
            || (big && header[2] == 0 && header[3] == 43))
            throw new NotSupportedException("BigTIFF is outside the current FilmMeta compatibility scope.");
        var tiff = (little && header[2] == 42 && header[3] == 0)
            || (big && header[2] == 0 && header[3] == 42);
        if (!jpeg && !tiff)
            throw new InvalidDataException("The file is not a JPEG, classic TIFF, or DNG image.");

        stream.Position = 0;
        var directories = ImageMetadataReader.ReadMetadata(stream);
        cancellationToken.ThrowIfCancellationRequested();
        var warnings = directories.SelectMany(d => d.Errors.Select(e => d.Name + ": " + e)).ToList();
        var isDng = Path.GetExtension(path).Equals(".dng", StringComparison.OrdinalIgnoreCase)
            || directories.OfType<ExifDirectoryBase>().Any(d => d.ContainsTag(DngVersionTag));
        var exif = ReadExif(directories);
        var xmp = ReadXmp(directories.OfType<XmpDirectory>(), warnings);
        return MetadataResolver.Resolve(new RawMetadata(path, isDng ? "DNG" : jpeg ? "JPEG" : "TIFF",
            isDng, new ReadOnlyDictionary<string, string>(exif),
            new ReadOnlyDictionary<string, string>(xmp), warnings.AsReadOnly()));
    }

    private static Dictionary<string, string> ReadExif(IReadOnlyList<MetadataExtractor.Directory> directories)
    {
        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var directory in directories.OfType<ExifIfd0Directory>())
        {
            Add(directory, ExifDirectoryBase.TagMake, "Exif.Image.Make");
            Add(directory, ExifDirectoryBase.TagModel, "Exif.Image.Model");
        }
        foreach (var directory in directories.OfType<ExifSubIfdDirectory>())
        {
            Add(directory, ExifDirectoryBase.TagLensMake, "Exif.Photo.LensMake");
            Add(directory, ExifDirectoryBase.TagLensModel, "Exif.Photo.LensModel");
            Add(directory, ExifDirectoryBase.TagLensSerialNumber, "Exif.Photo.LensSerialNumber");
            Add(directory, ExifDirectoryBase.TagIsoEquivalent, "Exif.Photo.ISOSpeedRatings");
            Add(directory, ExifDirectoryBase.TagRecommendedExposureIndex, "Exif.Photo.RecommendedExposureIndex");
            Add(directory, ExifDirectoryBase.TagIsoSpeed, "Exif.Photo.ISOSpeed");
        }
        return values;

        void Add(MetadataExtractor.Directory directory, int id, string key)
        {
            if (!directory.ContainsTag(id))
                return;
            var raw = directory.GetObject(id);
            var value = raw is Array array && raw is not byte[]
                ? string.Join(", ", array.Cast<object>().Select(x => Convert.ToString(x, CultureInfo.InvariantCulture)?.Trim() ?? "").Distinct())
                : directory.GetString(id)?.Trim() ?? "";
            if (value.Length != 0)
                values.TryAdd(key, value);
        }
    }

    private static Dictionary<string, string> ReadXmp(IEnumerable<XmpDirectory> directories, List<string> warnings)
    {
        var values = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var directory in directories)
        {
            if (directory.XmpMeta is not { } meta)
                continue;
            foreach (var field in FieldCatalog.Fields)
            {
                Add(meta, FieldCatalog.Namespace, field.XmpProperty, FieldCatalog.Prefix + field.XmpProperty);
                if (field.AnalogProperty is not null)
                {
                    Add(meta, FieldCatalog.AnalogNamespace, field.AnalogProperty, FieldCatalog.AnalogPrefix + field.AnalogProperty);
                    Add(meta, FieldCatalog.AnalogNamespace + "/", field.AnalogProperty, FieldCatalog.AnalogPrefix + field.AnalogProperty);
                }
                foreach (var tag in field.StandardXmp)
                {
                    var parts = tag.Split('.');
                    var ns = parts[1] switch
                    {
                        "tiff" => "http://ns.adobe.com/tiff/1.0/",
                        "exif" => "http://ns.adobe.com/exif/1.0/",
                        "exifEX" => "http://cipa.jp/exif/1.0/",
                        "aux" => "http://ns.adobe.com/exif/1.0/aux/",
                        _ => throw new InvalidOperationException("Unknown standard XMP schema.")
                    };
                    Add(meta, ns, parts[2], tag);
                }
            }
            foreach (var property in new[] { "DigitizationType", "SchemaVersion", "PreviousDigitizerExif" })
                Add(meta, FieldCatalog.Namespace, property, FieldCatalog.Prefix + property);
        }
        return values;

        void Add(IXmpMeta meta, string ns, string property, string key)
        {
            if (values.ContainsKey(key) || XmpMetaFactory.SchemaRegistry.GetNamespacePrefix(ns) is null)
                return;
            try
            {
                var item = meta.GetProperty(ns, property);
                if (item is null)
                    return;
                var value = item.Options.IsArray
                    ? string.Join(", ", Enumerable.Range(1, meta.CountArrayItems(ns, property))
                        .Select(i => meta.GetArrayItem(ns, property, i)?.Value?.Trim() ?? "").Distinct())
                    : item.Value?.Trim() ?? "";
                if (value.Length != 0)
                    values.Add(key, value);
            }
            catch (XmpException e)
            {
                warnings.Add(key + ": " + e.Message);
            }
        }
    }
}
