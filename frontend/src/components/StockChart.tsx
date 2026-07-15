import React, { useEffect, useRef } from 'react'
import { createChart, ColorType, IChartApi, ISeriesApi, CandlestickData, LineData, HistogramData } from 'lightweight-charts'

interface StockChartProps {
  symbol: string
  data?: {
    candlesticks: CandlestickData[]
    volume: HistogramData[]
    ma50?: LineData[]
    ma200?: LineData[]
  }
}

const StockChart: React.FC<StockChartProps> = ({ symbol, data }) => {
  const chartContainerRef = useRef<HTMLDivElement>(null)
  const chartRef = useRef<IChartApi | null>(null)

  useEffect(() => {
    if (!chartContainerRef.current) return

    const chart = createChart(chartContainerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: 'transparent' },
        textColor: '#d1d4dc',
      },
      grid: {
        vertLines: { color: '#2a2e39' },
        horzLines: { color: '#2a2e39' },
      },
      crosshair: {
        mode: 0,
      },
      rightPriceScale: {
        borderColor: '#2a2e39',
      },
      timeScale: {
        borderColor: '#2a2e39',
        timeVisible: false,
      },
      width: chartContainerRef.current.clientWidth,
      height: 450,
    })

    chartRef.current = chart

    // Candlestick series
    const candleSeries = chart.addCandlestickSeries({
      upColor: '#00b96b',
      downColor: '#ff4d4f',
      borderDownColor: '#ff4d4f',
      borderUpColor: '#00b96b',
      wickDownColor: '#ff4d4f',
      wickUpColor: '#00b96b',
    })

    // Volume series
    const volumeSeries = chart.addHistogramSeries({
      color: '#26a69a',
      priceFormat: {
        type: 'volume',
      },
      priceScaleId: 'volume',
    })

    chart.priceScale('volume').applyOptions({
      scaleMargins: {
        top: 0.85,
        bottom: 0,
      },
    })

    // MA series
    const ma50Series = chart.addLineSeries({
      color: '#2196F3',
      lineWidth: 1,
      priceLineVisible: false,
    })

    const ma200Series = chart.addLineSeries({
      color: '#FF9800',
      lineWidth: 1,
      priceLineVisible: false,
    })

    // Set data if provided
    if (data) {
      candleSeries.setData(data.candlesticks)
      if (data.volume) volumeSeries.setData(data.volume)
      if (data.ma50) ma50Series.setData(data.ma50)
      if (data.ma200) ma200Series.setData(data.ma200)
    }

    // Handle resize
    const handleResize = () => {
      if (chartContainerRef.current) {
        chart.applyOptions({ width: chartContainerRef.current.clientWidth })
      }
    }
    window.addEventListener('resize', handleResize)

    return () => {
      window.removeEventListener('resize', handleResize)
      chart.remove()
    }
  }, [symbol, data])

  return (
    <div
      ref={chartContainerRef}
      style={{ width: '100%', height: 450 }}
    />
  )
}

export default StockChart
