using System.Security.Cryptography;
using FilmMeta.Core;
using FilmMeta.Metadata;

namespace FilmMeta.Tests;

public sealed class CompatibilityTests
{
    public static IEnumerable<object[]> Cases => FixtureData.All.Select(f => new object[] { f.Name });

    [Theory]
    [MemberData(nameof(Cases))]
    public void ReadsExactlyLikePythonAndDoesNotModifyFile(string name)
    {
        using var folder = new TemporaryFolder();
        var fixture = FixtureData.Named(name);
        var path = folder.Save(fixture, "Кадр с пробелами");
        var before = SHA256.HashData(File.ReadAllBytes(path));
        var modified = File.GetLastWriteTimeUtc(path);
        var actual = new PhotoMetadataReader().Read(path);
        Assert.Equal(fixture.IsDng, actual.IsDng);
        Assert.Equal(fixture.Values.Count, actual.Values.Count);
        foreach (var (id, value) in fixture.Values)
            Assert.Equal(value, actual.Values[id]);
        foreach (var (id, source) in fixture.Sources)
            Assert.Equal(source, actual.Sources[id]);
        Assert.Equal(before, SHA256.HashData(File.ReadAllBytes(path)));
        Assert.Equal(modified, File.GetLastWriteTimeUtc(path));
        using var reopened = new FileStream(path, FileMode.Open, FileAccess.ReadWrite, FileShare.None);
        Assert.True(reopened.Length > 0);
    }

    [Theory]
    [InlineData("II+\0")]
    [InlineData("MM\0+")]
    public void RejectsBigTiff(string signature)
    {
        using var folder = new TemporaryFolder();
        var path = Path.Combine(folder.Path, "big.tif");
        File.WriteAllBytes(path, System.Text.Encoding.ASCII.GetBytes(signature + "0000"));
        Assert.Throws<NotSupportedException>(() => new PhotoMetadataReader().Read(path));
    }

    [Theory]
    [InlineData("")]
    [InlineData("not an image")]
    [InlineData("II*")]
    public void RejectsInvalidInput(string content)
    {
        using var folder = new TemporaryFolder();
        var path = Path.Combine(folder.Path, "broken.jpg");
        File.WriteAllText(path, content);
        Assert.Throws<InvalidDataException>(() => new PhotoMetadataReader().Read(path));
    }

    [Fact]
    public void RefusesUnsupportedExtension()
    {
        using var folder = new TemporaryFolder();
        var path = Path.Combine(folder.Path, "data.txt");
        File.WriteAllText(path, "text");
        Assert.Throws<NotSupportedException>(() => new PhotoMetadataReader().Read(path));
    }

    [Fact]
    public void ChecksCancellationBeforeOpeningFile()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        Assert.Throws<OperationCanceledException>(() => new PhotoMetadataReader().Read("missing.jpg", cancellation.Token));
    }

    [Fact]
    public void CatalogKeepsExistingVisibleFields()
    {
        Assert.Equal(29, FieldCatalog.Fields.Count);
        Assert.Equal(14, FieldCatalog.Fields.Count(f => f.DefaultVisible));
        Assert.All(FieldCatalog.Fields, f => Assert.Equal(f.Role + "." + f.Field, f.Id));
    }
}
