using System.Text.Json;
using FilmMeta.Cli;
using FilmMeta.Core;
using FilmMeta.Metadata;

namespace FilmMeta.Tests;

public sealed class CliTests
{
    [Theory]
    [InlineData("--help")]
    [InlineData("--version")]
    [InlineData("fields")]
    public void InformationalCommandsDoNotReadImages(string command)
    {
        using var output = new StringWriter();
        using var error = new StringWriter();
        Assert.Equal(0, new CliApplication(new FailingReader()).Run(new[] { command }, output, error));
        Assert.NotEmpty(output.ToString());
        Assert.Empty(error.ToString());
    }

    [Theory]
    [InlineData("write")]
    [InlineData("read", "--unknown")]
    [InlineData("read")]
    public void InvalidArgumentsDoNotReadImages(params string[] args)
    {
        using var output = new StringWriter();
        using var error = new StringWriter();
        Assert.Equal(2, new CliApplication(new FailingReader()).Run(args, output, error));
        Assert.Empty(output.ToString());
        Assert.NotEmpty(error.ToString());
    }

    [Fact]
    public void ReportsOneBrokenFileAndStillReadsTheNext()
    {
        using var folder = new TemporaryFolder();
        var good = folder.Save(FixtureData.Named("own-jpeg"));
        var bad = Path.Combine(folder.Path, "broken.jpg");
        File.WriteAllText(bad, "broken");
        using var output = new StringWriter();
        using var error = new StringWriter();
        var code = new CliApplication(new PhotoMetadataReader()).Run(
            new[] { "read", bad, good, "--json" }, output, error);
        var report = JsonDocument.Parse(output.ToString()).RootElement;
        Assert.Equal(1, code);
        Assert.Single(report.GetProperty("files").EnumerateArray());
        Assert.Single(report.GetProperty("errors").EnumerateArray());
        Assert.Empty(error.ToString());
    }

    [Fact]
    public void DeduplicatesExplicitAndFolderInputAndHonoursRecursion()
    {
        using var folder = new TemporaryFolder();
        var first = folder.Save(FixtureData.Named("own-jpeg"));
        var nested = Path.Combine(folder.Path, "nested");
        System.IO.Directory.CreateDirectory(nested);
        File.WriteAllBytes(Path.Combine(nested, "frame.tif"), Convert.FromBase64String(FixtureData.Named("own-tiff").Data));
        using var output = new StringWriter();
        using var error = new StringWriter();
        var code = new CliApplication(new PhotoMetadataReader()).Run(
            new[] { "read", first, folder.Path, "--recursive", "--json" }, output, error);
        Assert.Equal(0, code);
        Assert.Equal(2, JsonDocument.Parse(output.ToString()).RootElement.GetProperty("files").GetArrayLength());
    }

    [Fact]
    public void FolderWithoutImagesIsAnError()
    {
        using var folder = new TemporaryFolder();
        using var output = new StringWriter();
        using var error = new StringWriter();
        Assert.Equal(1, new CliApplication(new PhotoMetadataReader()).Run(
            new[] { "read", folder.Path, "--json" }, output, error));
        var report = JsonDocument.Parse(output.ToString()).RootElement;
        Assert.Empty(report.GetProperty("files").EnumerateArray());
        Assert.Single(report.GetProperty("errors").EnumerateArray());
    }

    [Fact]
    public void CancellationProducesACompleteJsonReport()
    {
        using var cancellation = new CancellationTokenSource();
        cancellation.Cancel();
        using var output = new StringWriter();
        using var error = new StringWriter();
        Assert.Equal(130, new CliApplication(new FailingReader()).Run(
            new[] { "read", "missing.jpg", "--json" }, output, error, cancellation.Token));
        Assert.True(JsonDocument.Parse(output.ToString()).RootElement.GetProperty("cancelled").GetBoolean());
    }

    private sealed class FailingReader : IMetadataReader
    {
        public MetadataSnapshot Read(string path, CancellationToken cancellationToken = default) =>
            throw new InvalidOperationException("This command must not read a file.");
    }
}
