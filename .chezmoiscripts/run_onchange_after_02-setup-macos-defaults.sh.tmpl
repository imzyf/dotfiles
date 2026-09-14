#!/bin/zsh
# 使用 zsh 运行此脚本。
# 命令失败或引用未设置的变量时退出，并将管道中任一命令的失败视为管道失败。
set -euo pipefail

# 在非 macOS 系统上直接退出，跳过以下设置。
[[ "$OSTYPE" == darwin* ]] || exit 0

# 使用深色系统外观。
defaults write NSGlobalDomain AppleInterfaceStyle -string Dark
# 首选语言设为英语（美国），第二语言设为简体中文（中国大陆）。
defaults write NSGlobalDomain AppleLanguages -array en-US zh-Hans-CN
# 使用英语（美国）的区域格式。
defaults write NSGlobalDomain AppleLocale -string "en_US"
# 将首选长度单位设为厘米。
defaults write NSGlobalDomain AppleMeasurementUnits -string Centimeters
# 启用公制计量单位。
defaults write NSGlobalDomain AppleMetricUnits -bool true
# 关闭长按按键时的重音字符菜单，以允许长按连续输入。
defaults write NSGlobalDomain ApplePressAndHoldEnabled -bool false
# 使用摄氏度显示温度。
defaults write NSGlobalDomain AppleTemperatureUnit -string Celsius

# 将长按按键开始连续输入前的延迟设为 15；数值越小，等待时间越短。
defaults write NSGlobalDomain InitialKeyRepeat -int 15
# 将连续输入的按键重复间隔设为 2；数值越小，重复速度越快。
defaults write NSGlobalDomain KeyRepeat -int 2
# 关闭将输入的连字符自动替换为破折号的功能。
defaults write NSGlobalDomain NSAutomaticDashSubstitutionEnabled -bool false
# 关闭将直引号自动替换为智能引号的功能。
defaults write NSGlobalDomain NSAutomaticQuoteSubstitutionEnabled -bool false
# 关闭自动拼写纠正。
defaults write NSGlobalDomain NSAutomaticSpellingCorrectionEnabled -bool false

# 将屏幕右上角的触发角操作设为启动屏幕保护程序（操作值 5）。
defaults write com.apple.dock wvous-tr-corner -int 5
# 将 Dock 图标大小设为 40 点。
defaults write com.apple.dock tilesize -int 40
# 将 Dock 放在屏幕左侧。
defaults write com.apple.dock orientation -string left

# 在 Finder 中显示隐藏文件；也可使用 Command + Shift + . 快捷键切换。
defaults write com.apple.finder AppleShowAllFiles -bool true
# 将 Finder 的默认搜索范围设为当前文件夹（SCev）。
defaults write com.apple.finder FXDefaultSearchScope -string SCev
# 在 Finder 窗口底部显示路径栏。
defaults write com.apple.finder ShowPathbar -bool true
# 在 Finder 窗口底部显示状态栏。
defaults write com.apple.finder ShowStatusBar -bool true
# 关闭修改文件扩展名时的警告。
defaults write com.apple.finder FXEnableExtensionChangeWarning -bool false
# 将 Finder 的首选显示方式设为列表视图（Nlsv）。
defaults write com.apple.finder FXPreferredViewStyle -string Nlsv
# 将 Finder 新窗口的打开目标设为下方 URL 指定的文件夹（PfLo）。
defaults write com.apple.finder NewWindowTarget -string PfLo
# 让 Finder 新窗口打开当前用户的 Downloads 文件夹。
defaults write com.apple.finder NewWindowTargetPath -string "file://$HOME/Downloads/"
# 隐藏桌面上的内置硬盘图标。
defaults write com.apple.finder ShowHardDrivesOnDesktop -bool false

# 结束 ControlCenter、Dock 和 Finder 进程，使其重新启动时加载偏好设置。
killall ControlCenter Dock Finder
# 将用户设置应用到当前会话，包括更新后的按键重复设置。
/System/Library/PrivateFrameworks/SystemAdministration.framework/Resources/activateSettings -u
# 输出原有的下次登录生效提示；此脚本未设置提示中提到的 TISRomanSwitchState。
echo "AppleLanguages, AppleInterfaceStyle, and TISRomanSwitchState take effect at next login."
