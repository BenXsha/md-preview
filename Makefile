# md-preview 常用任务（没有 make 也可以直接看目标里的命令）
.PHONY: help test test-fast install uninstall gallery probe demo run version

help:  ## 显示所有任务
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

test:  ## 跑全部测试（含需要浏览器的端到端）
	python3 -m pytest -q

test-fast:  ## 只跑不需要浏览器的测试
	python3 -m pytest -q -k "not end_to_end"

install:  ## 用户级安装（脚本 + desktop + Dolphin 中键顺序）
	./contrib/install.sh

uninstall:  ## 卸载（保留主题与配置）
	./contrib/uninstall.sh

gallery:  ## 给所有主题截图并拼版（需要 Pillow）
	python3 tools/theme-gallery.py

probe:  ## 抽查几个主题是否真的命中 DOM（需要 websockets）
	python3 tools/probe-styles.py github newsprint night drake-jb

demo:  ## 录一段 README 用的演示动图（需要 websockets + Pillow，可选 ffmpeg）
	python3 tools/middle-click-demo.py --caption "Dolphin middle-click: .md → a themed PDF"

run:  ## 用测试文档跑一遍（真实产物，会打开阅读器）
	./bin/md-preview tests/sample.md

version:  ## 打印版本
	./bin/md-preview --version
