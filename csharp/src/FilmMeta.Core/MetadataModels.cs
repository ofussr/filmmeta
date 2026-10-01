namespace FilmMeta.Core;

public sealed record RawMetadata(
    string Path, string Format, bool IsDng,
    IReadOnlyDictionary<string, string> Exif,
    IReadOnlyDictionary<string, string> Xmp,
    IReadOnlyList<string> Warnings);

public sealed record MetadataSnapshot(
    string Path, string Format, bool IsDng,
    IReadOnlyDictionary<string, string> Values,
    IReadOnlyDictionary<string, string> Sources,
    IReadOnlyDictionary<string, string> Exif,
    IReadOnlyDictionary<string, string> Xmp,
    IReadOnlyList<string> Warnings);

public interface IMetadataReader
{
    MetadataSnapshot Read(string path, CancellationToken cancellationToken = default);
}
