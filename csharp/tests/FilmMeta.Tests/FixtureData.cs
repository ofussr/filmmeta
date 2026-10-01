using System.Text.Json;

namespace FilmMeta.Tests;

public sealed record OracleFixture(string Name, string Extension, string Data,
    Dictionary<string, string> Values, Dictionary<string, string> Sources, bool IsDng);

public static class FixtureData
{
    public static IReadOnlyList<OracleFixture> All { get; } =
        JsonSerializer.Deserialize<List<OracleFixture>>(File.ReadAllText(
            Path.Combine(AppContext.BaseDirectory, "Fixtures", "python-oracle.json")),
            new JsonSerializerOptions(JsonSerializerDefaults.Web))!;

    public static OracleFixture Named(string name) => All.Single(f => f.Name == name);
}

public sealed class TemporaryFolder : IDisposable
{
    public string Path { get; } = System.IO.Path.Combine(System.IO.Path.GetTempPath(),
        "FilmMeta-" + Guid.NewGuid().ToString("N"), "Фото", "Мирущенко Михаил");

    public TemporaryFolder() => System.IO.Directory.CreateDirectory(Path);

    public string Save(OracleFixture fixture, string? name = null)
    {
        var file = System.IO.Path.Combine(Path, (name ?? fixture.Name) + fixture.Extension);
        File.WriteAllBytes(file, Convert.FromBase64String(fixture.Data));
        return file;
    }

    public void Dispose()
    {
        var root = System.IO.Directory.GetParent(System.IO.Directory.GetParent(Path)!.FullName)!.FullName;
        System.IO.Directory.Delete(root, recursive: true);
    }
}
