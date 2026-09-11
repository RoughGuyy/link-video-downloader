# Link Video Downloader

一个链接就能下载**公开可访问**的小红书、B站和 YouTube 视频。

- 自动识别平台与短链接
- 可选择 `2160p / 1440p / 1080p / 720p / 480p / 360p` 或最佳画质
- 可列出可用格式、指定格式编号和偏好 H.264/HEVC
- 小红书使用内置解析
- B站与 YouTube 使用 `yt-dlp`
- 安装时自动提供 FFmpeg，用于合并最高质量音视频
- 优先使用系统 FFmpeg，否则使用项目环境内的独立版本
- Windows、macOS、Linux 均可使用

## Windows 免安装版（推荐）

从 [Releases](https://github.com/RoughGuyy/link-video-downloader/releases) 下载 `LinkVideoDownloader.exe`，双击即可打开图形界面。程序内可粘贴链接、选择保存位置、清晰度和编码，不需要安装 Python、Conda 或 FFmpeg。

Windows 首次运行未知发布者的自编译程序时，可能会显示 SmartScreen 提示。你也可以从源码自行构建并核对代码。

> 请只下载你拥有权利或已获授权保存的内容，并遵守平台条款与当地法律。本项目不绕过 DRM、付费墙、登录限制或其他访问控制。

## 安装

需要 Python 3.10 或更高版本。

### Windows 简单方式

1. 下载并解压项目。
2. 双击 `setup_windows.bat` 完成首次安装。
3. 以后双击 `download_video.bat`，粘贴链接并按回车即可。

下载的视频默认保存在项目内的 `downloads` 文件夹。

### Miniconda / Anaconda 方式

如果电脑上已经安装了 Miniconda 或 Anaconda：

1. 双击 `setup_conda_windows.bat`，它会创建独立环境 `link-video-downloader`。
2. 以后双击 `download_video_conda.bat` 即可粘贴链接下载。

也可以手动安装：

```bash
conda create -n link-video-downloader python=3.11 pip -y
conda run -n link-video-downloader python -m pip install -e .
conda run -n link-video-downloader linkvideo "视频链接" --quality 1080p
```

### 命令行方式

```bash
git clone https://github.com/RoughGuyy/link-video-downloader.git
cd link-video-downloader
python -m pip install -e .
```

安装项目时会通过 `imageio-ffmpeg` 自动准备一个项目专用的 FFmpeg，不需要修改系统环境变量。若电脑上已经安装了 FFmpeg，程序会优先使用系统版本。

FFmpeg 用于把 B站和 YouTube 分开提供的高清画面与音频合并成一个 MP4。小红书的普通 MP4 下载通常不需要它。

## 使用

直接输入链接：

```bash
linkvideo "https://www.xiaohongshu.com/explore/..."
linkvideo "https://www.bilibili.com/video/BV..."
linkvideo "https://www.youtube.com/watch?v=..."
```

不带参数运行时，会提示你粘贴链接：

```bash
linkvideo
```

指定保存目录：

```bash
linkvideo "视频链接" --output "D:/Videos"
```

选择最高下载清晰度（三个平台通用）：

```bash
# 默认：最高可用质量
linkvideo "视频链接" --quality best

# 最高不超过 1080p；若没有，会选择最接近的可用格式
linkvideo "视频链接" --quality 1080p
linkvideo "视频链接" -q 720p
```

先查看链接提供的全部格式：

```bash
linkvideo "视频链接" --list-formats
```

再按格式编号下载：

```bash
linkvideo "视频链接" --format-id 137
```

选择编码偏好；没有匹配格式时会自动回退：

```bash
linkvideo "视频链接" --codec h264
linkvideo "视频链接" --codec hevc
```

实际可用清晰度和编码由原始页面决定。项目会自动调用 FFmpeg 合并 B站和 YouTube 的最高质量视频与音频。

## 开发与测试

```bash
python -m pip install -e .
python -m unittest discover -s tests -v
```

项目包含 GitHub Actions，会在 Python 3.10–3.13 上自动运行测试。

构建 Windows 单文件程序：

```bash
python -m pip install -e ".[build]"
build_exe.bat
```

生成文件位于 `release/LinkVideoDownloader.exe`。推送 `v*` 标签时，GitHub Actions 也会自动构建 EXE 并发布到 Releases。

## 工作方式

- **小红书**：读取公开分享页里已经提供的视频流信息，选择合适的 MP4 并保存。
- **B站 / YouTube**：调用 `yt-dlp` 的 Python API，并使用项目自带或系统中的 FFmpeg 合并最佳视频和音频。

站点页面结构会变化。如果 B站或 YouTube 下载突然失效，请先升级 `yt-dlp`：

```bash
python -m pip install -U yt-dlp
```

如果是小红书解析失效，请拉取本项目的最新代码后重新运行 `python -m pip install -e .`。

## 发布到你的 GitHub

先在 GitHub 创建名为 `link-video-downloader` 的空仓库，然后运行：

```bash
git init -b main
git add .
git commit -m "Initial release"
git remote add origin https://github.com/RoughGuyy/link-video-downloader.git
git push -u origin main
```

## License

[MIT](LICENSE)
