# VeighNa框架的MultiCharts数据服务接口

<p align="center">
  <img src ="https://vnpy.oss-cn-shanghai.aliyuncs.com/vnpy-logo.png"/>
</p>

<p align="center">
    <img src ="https://img.shields.io/badge/version-1.0.3-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg" />
    <img src ="https://img.shields.io/github/license/vnpy/vnpy.svg?color=orange"/>
</p>

## 说明

基于艾杨软件MultiCharts的数据服务接口，支持以下中国金融市场的K线和Tick数据：

* 期货和期货期权：
  * CFFEX：中国金融期货交易所
  * SHFE：上海期货交易所
  * DCE：大连商品交易所
  * CZCE：郑州商品交易所
  * INE：上海国际能源交易中心
  * GFEX：广州期货交易所
* 股票和ETF期权：
  * SSE：上海证券交易所
  * SZSE：深圳证券交易所


## 安装

安装环境推荐基于4.0.0版本以上的【[**VeighNa Studio**](https://www.vnpy.com)】。

直接使用pip命令：

```
pip install vnpy_mcdata
```


或者下载源代码后，解压后在cmd中运行：

```
pip install .
```


## 使用

在VeighNa中使用MultiCharts数据接口时，需要在全局配置中填写以下字段信息：

|名称|含义|必填|举例|
|---------|----|---|---|
|datafeed.name|名称|是|mcdata|
|datafeed.username|MultiCharts安装所在目录|是|C:/MCTrader14/APPs|
