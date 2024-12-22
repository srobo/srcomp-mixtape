from . import cli

try:
    cli.main()
except cli.IncorrectDirectoryArgumentException:
    print("File entered for the playlist when directory expected!")