# PIP PyPI Mirror Sources

## Reference
- [pip pypi page](https://pypi.org/project/pip/)
- [The Python Package Index (PyPI)](https://pypi.org/)
- [PyPI docs](https://pip.pypa.io/en/stable/)
- [PyPI docs: user guide](https://pip.pypa.io/en/stable/user_guide/)
- [Python Installing Packages](https://packaging.python.org/tutorials/installing-packages/)
- [Github project: pypi-mirrors](https://github.com/ibigbug/pypi-mirrors)
- [Python pip 安装与使用](https://www.runoob.com/w3cnote/python-pip-install-usage.html)
- [从国内的 PyPI 镜像（源）安装 Python 包](https://zhuanlan.zhihu.com/p/57872888)

## Some tools use pypi
- easy_install
- pip
- conda
- pipenv
- poetry
- flit

## Some pypi mirrors
> 官方
- https://pypi.org/simple/
> 豆瓣
- http://pypi.doubanio.com/simple
- https://pypi.douban.com/simple
- http://pypi.doubanio.com/simple
- https://pypi.doubanio.com/simple
> 清华大学
- https://pypi.tuna.tsinghua.edu.cn/simple
> 中国科技大学
- https://pypi.mirrors.ustc.edu.cn/simple/
- https://mirrors.bfsu.edu.cn/pypi/web/simple/
> 阿里云
- http://mirrors.aliyun.com/pypi/simple/
- https://mirrors.aliyun.com/pypi/simple/
> 腾讯云
- https://mirrors.cloud.tencent.com/pypi/simple/
> 网易
- http://mirrors.163.com/pypi/simple/
- https://mirrors.163.com/pypi/simple/


## 安装 pip
> run ensurepip
```sh
python -m ensurepip --default-pip
```

> curl & run shell script
```sh
python -c "$(curl -fsSL https://bootstrap.pypa.io/get-pip.py)"
```

> wget & run shell script
```sh
python -c "$(wget https://bootstrap.pypa.io/get-pip.py -O -)"
```

## 临时使用镜像源，如有报错需要指定 --trusted-host
```sh
pip install -i pypi-mirror-url [--trusted-host pypi-mirror-host] some-packages
```

**注意** 使用 https 协议的镜像源要求安装有 ssl 且配置正确

## 列出已经设置的配置
```sh
pip config list
```

## 设置源
```sh
pip config set global.index-url pypi-mirror-url
```

## 获取已经设置的源
```sh
pip config get global.index-url
```

## 配置文件路径
https://pip.pypa.io/en/stable/user_guide/#config-file

## 一些基本操作
> 安装包
```sh
# 可通过使用 ==, >=, <=, >, < 来指定一个版本号，不指定则安装最新版
pip install <package>
```

> 升级包
```sh
pip install --upgrade/-U <package>
```

> 卸载包
```sh
pip uninstall <package>
```

> 搜索包
```sh
pip search <package>
```

> 显示包的信息
```sh
pip show <package>
```

> 显示包的详细信息
```sh
pip show -f <package>
```

> 列出已安装的包
```sh
pip list
```

> 列出可升级的包
```sh
pip list -o
```

> 列出已安装的包，以 requirements 格式
```sh
pip freeze >requirements.txt
```

> 安装 requirements.txt 中列举的包
```sh
pip install -r requirements.txt
```

> 列出已安装的包
```sh
conda list
```

> 列出已安装的包，以 requirements 格式
```sh
conda list -e
```

> 安装 requirements.txt 中列举的包
```sh
conda install --yes --file requirements.txt
```
