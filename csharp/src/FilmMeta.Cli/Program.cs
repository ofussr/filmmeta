using System.Text;
using FilmMeta.Cli;
using FilmMeta.Metadata;

Console.OutputEncoding = new UTF8Encoding(false);
using var cancellation = new CancellationTokenSource();
ConsoleCancelEventHandler cancel = (_, e) => { e.Cancel = true; cancellation.Cancel(); };
Console.CancelKeyPress += cancel;
try
{
    return new CliApplication(new PhotoMetadataReader()).Run(args, Console.Out, Console.Error, cancellation.Token);
}
finally
{
    Console.CancelKeyPress -= cancel;
}
