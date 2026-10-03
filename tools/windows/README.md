# Windows ExifTool

Place Windows ExifTool here before building on Windows:

```text
tools/windows/exiftool.exe
tools/windows/exiftool_files/
```

The official Windows download is a zip containing `exiftool(-k).exe` and an
`exiftool_files` folder. Copy both here and rename the executable to
`exiftool.exe` for packaging. The executable does not work without the
`exiftool_files` folder next to it.

Both are ignored by git.
