import React from 'react'
import { useParams } from 'react-router-dom'
import { Card, Typography, Spin, Row, Col, Tag, Descriptions, Space, Alert } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { getStockDetail, getStockPrice } from '../services/api'
import type { StockDetailData, StockPriceData } from '../services/types'
import StockChart from '../components/StockChart'

const { Title, Text } = Typography

const StockDetail: React.FC = () => {
  const { symbol } = useParams<{ symbol: string }>()

  const { data: rawData, isLoading } = useQuery({
    queryKey: ['stock', symbol],
    queryFn: () => getStockDetail(symbol!).then(r => r.data.data as StockDetailData),
    enabled: !!symbol,
  })

  const { data: priceRaw } = useQuery({
    queryKey: ['stock-price', symbol],
    queryFn: () => getStockPrice(symbol!).then(r => r.data as unknown as StockPriceData),
    enabled: !!symbol,
  })

  const d = rawData as StockDetailData | undefined

  // Transform price API response → chart data
  const chartData = React.useMemo(() => {
    const prices = priceRaw?.prices
    if (!prices) return undefined
    const dates = Object.keys(prices).sort()
    const candlesticks = dates.map(date => ({
      time: date,
      open: prices[date].open,
      high: prices[date].high,
      low: prices[date].low,
      close: prices[date].close,
    }))
    const volume = dates.map((date, i, arr) => {
      const prev = i > 0 ? arr[i - 1] : null
      const prevClose = prev ? prices[prev].close : prices[date].close
      const isUp = prices[date].close >= prevClose
      return {
        time: date,
        value: prices[date].volume,
        color: isUp ? 'rgba(0,185,107,0.3)' : 'rgba(255,77,79,0.3)',
      }
    })
    return { candlesticks, volume }
  }, [priceRaw])

  if (isLoading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  const signalColor = d?.signal === 'buy' ? 'green' : d?.signal === 'watch' ? 'orange' : d?.signal === 'extended' ? '#999' : 'default'
  const signalText = d?.signal === 'buy' ? '买入' : d?.signal === 'watch' ? '关注' : d?.signal === 'extended' ? '已延伸' : '--'
  const stage2Color = d?.stage2 ? 'green' : 'red'
  const patternExtended = d?.signal === 'extended'

  return (
    <div>
      <Title level={4}>
        {symbol}
        {d?.current_price ? <Text style={{ fontSize: 16, marginLeft: 12 }}>¥{d.current_price}</Text> : null}
        <Tag color={signalColor} style={{ marginLeft: 12 }}>{signalText}</Tag>
        <Tag color={stage2Color}>{d?.stage2 ? 'Stage 2' : '非 Stage 2'}</Tag>
      </Title>

      <Row gutter={[16, 16]}>
        <Col xs={24}>
          <Card style={{ height: 500 }}>
            <StockChart symbol={symbol || ''} data={chartData} />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        {/* 技术指标 */}
        <Col xs={24} md={8}>
          <Card title="技术指标" size="small">
            <Descriptions column={1} size="small" colon={false}>
              <Descriptions.Item label="最新价">
                <Text strong>{d?.current_price?.toFixed(2) || '--'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="RS 评分">
                <Text strong style={{ color: (d?.rs_rating || 0) >= 80 ? '#00b96b' : '#faad14' }}>
                  {d?.rs_rating ?? '--'}/99
                </Text>
              </Descriptions.Item>
              <Descriptions.Item label="RS 排名">
                {d?.rs_rank != null ? `${d.rs_rank}%` : '--'}
              </Descriptions.Item>
              <Descriptions.Item label="综合评分">
                <Text strong>{d?.score?.toFixed(1) ?? '--'}</Text>
              </Descriptions.Item>
              <Descriptions.Item label="阶段">
                <Tag color={stage2Color}>{d?.stage2 ? 'Stage 2 上升趋势' : '非 Stage 2'}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="信号">
                <Tag color={signalColor}>{signalText}</Tag>
              </Descriptions.Item>
              <Descriptions.Item label="精选理由" span={24}>
                <Text style={{ fontSize: 12 }}>{d?.reason || '--'}</Text>
              </Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>

        {/* 形态详情 */}
        <Col xs={24} md={8}>
          <Card title="形态详情" size="small">
            {d?.pattern_detail?.detected ? (
              <>
                {patternExtended && (
                  <Alert type="warning" showIcon message="该形态已延伸，买入点已过期，等待新形态形成" style={{ marginBottom: 12 }} />
                )}
              <Descriptions column={1} size="small" colon={false}>
                <Descriptions.Item label="形态类型">
                  <Tag color={patternExtended ? 'default' : 'blue'}>{d.pattern_detail.type || d.pattern}</Tag>
                  {patternExtended && <Tag color="orange">已延伸</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="置信度">
                  <Tag color={d.pattern_detail.confidence === 'high' ? 'green' : 'orange'}>
                    {d.pattern_detail.confidence === 'high' ? '高' : '中'}
                  </Tag>
                </Descriptions.Item>
                <Descriptions.Item label="买点">
                  {d.pattern_detail.buy_point
                    ? <Text strong style={{ color: patternExtended ? '#bbb' : undefined, textDecoration: patternExtended ? 'line-through' : undefined }}>¥{d.pattern_detail.buy_point}</Text>
                    : '--'}
                </Descriptions.Item>
                <Descriptions.Item label="止损价">
                  {d.pattern_detail.stop_price
                    ? <Text style={{ color: patternExtended ? '#bbb' : '#ff4d4f', textDecoration: patternExtended ? 'line-through' : undefined }}>¥{d.pattern_detail.stop_price}</Text>
                    : '--'}
                </Descriptions.Item>
                <Descriptions.Item label="目标价">
                  {d.pattern_detail.target_price
                    ? <Text style={{ color: patternExtended ? '#bbb' : '#00b96b', textDecoration: patternExtended ? 'line-through' : undefined }}>¥{d.pattern_detail.target_price}</Text>
                    : '--'}
                </Descriptions.Item>
                <Descriptions.Item label="盈亏比">
                  {d.pattern_detail.buy_point && d.pattern_detail.stop_price
                    ? <Text style={{ color: patternExtended ? '#bbb' : undefined }}>{((d.pattern_detail.buy_point - d.pattern_detail.stop_price) / d.pattern_detail.stop_price * 100).toFixed(1) + '%'}</Text>
                    : '--'}
                </Descriptions.Item>
                <Descriptions.Item label="识别详情" span={24}>
                  <Text style={{ fontSize: 12 }}>{d.pattern_detail.reason || '--'}</Text>
                </Descriptions.Item>
              </Descriptions>
              </>
            ) : (
              <Text type="secondary">暂无形态识别</Text>
            )}

            {/* 止损信息 */}
            {d?.stop_loss ? (
              <>
                <div style={{ borderTop: '1px solid #f0f0f0', margin: '12px 0' }} />
                <Text strong style={{ fontSize: 13 }}>止损设置</Text>
                <Descriptions column={1} size="small" colon={false} style={{ marginTop: 8 }}>
                  <Descriptions.Item label="止损价">
                    {d.stop_loss.stop_price ? <Text type="danger">¥{d.stop_loss.stop_price}</Text> : '--'}
                  </Descriptions.Item>
                  <Descriptions.Item label="止损幅度">
                    {d.stop_loss.stop_pct != null ? `${d.stop_loss.stop_pct}%` : '--'}
                  </Descriptions.Item>
                  <Descriptions.Item label="止损方法">
                    <Tag>{d.stop_loss.method === 'atr' ? 'ATR' : '支撑位'}</Tag>
                  </Descriptions.Item>
                  <Descriptions.Item label="追踪止损">
                    {d.stop_loss.trailing_active ? <Tag color="green">已启用</Tag> : <Tag>未启用</Tag>}
                  </Descriptions.Item>
                </Descriptions>
              </>
            ) : null}
          </Card>
        </Col>

        {/* 突破信息 */}
        <Col xs={24} md={8}>
          <Card title="突破状态" size="small">
            {d?.breakout ? (
              <Descriptions column={1} size="small" colon={false}>
                <Descriptions.Item label="突破">
                  {d.breakout.detected
                    ? <Tag color="green">已突破</Tag>
                    : <Tag color="default">未突破</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="突破价格">
                  {d.breakout.breakout_price ? `¥${d.breakout.breakout_price}` : '--'}
                </Descriptions.Item>
                <Descriptions.Item label="突破日期">
                  {d.breakout.breakout_date || '--'}
                </Descriptions.Item>
                <Descriptions.Item label="成交量比">
                  {d.breakout.volume_ratio ? `${d.breakout.volume_ratio}x` : '--'}
                </Descriptions.Item>
                <Descriptions.Item label="突破天数">
                  {d.breakout.days_since_breakout != null ? `${d.breakout.days_since_breakout} 天` : '--'}
                </Descriptions.Item>
                <Descriptions.Item label="跟进买入">
                  {d.breakout.follow_through ? <Tag color="green">是</Tag> : <Tag>否</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="回踩买点">
                  {d.breakout.pullback_to_buy_point ? <Tag color="orange">回踩中</Tag> : <Tag>否</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="突破失败">
                  {d.breakout.failed_breakout ? <Tag color="red">是</Tag> : <Tag>否</Tag>}
                </Descriptions.Item>
                <Descriptions.Item label="详情" span={24}>
                  <Text style={{ fontSize: 12 }}>{d.breakout.reason || '--'}</Text>
                </Descriptions.Item>
              </Descriptions>
            ) : (
              <Text type="secondary">暂无突破数据</Text>
            )}
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default StockDetail
