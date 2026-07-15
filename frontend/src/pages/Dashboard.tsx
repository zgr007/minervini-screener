import React from 'react'
import { Row, Col, Card, Statistic, Table, Tag, Typography, Spin } from 'antd'
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  StockOutlined,
  TeamOutlined,
  FundOutlined,
  RiseOutlined,
  FallOutlined,
} from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { getDashboard, getTodaySignals, getScreenResults } from '../services/api'
import type { DashboardData, Signal, ScreenResult } from '../services/types'

const { Title, Text } = Typography

const Dashboard: React.FC = () => {
  const { data: dashData, isLoading: dashLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => getDashboard().then(r => r.data.data),
  })

  const { data: signalsData } = useQuery({
    queryKey: ['signals-today'],
    queryFn: () => getTodaySignals().then(r => r.data.data),
  })

  const { data: screenData } = useQuery({
    queryKey: ['screen-results'],
    queryFn: () => getScreenResults().then(r => r.data.data),
  })

  if (dashLoading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  const dashboard = dashData as DashboardData | undefined
  const signals = signalsData as Signal[] | undefined
  const screenResults = screenData as ScreenResult[] | undefined

  const columns = [
    { title: '代码', dataIndex: 'symbol', key: 'symbol', width: 80 },
    { title: '名称', dataIndex: 'name', key: 'name', render: (v: string, r: ScreenResult) => v && v !== r.symbol ? v : <Text type="secondary">--</Text> },
    { title: '综合评分', dataIndex: 'total_score', key: 'total_score', sorter: (a: ScreenResult, b: ScreenResult) => b.total_score - a.total_score, render: (v: number) => { const c = v >= 80 ? '#00b96b' : v >= 60 ? '#faad14' : v > 0 ? '#ff4d4f' : '#999'; return <Text strong style={{ color: c }}>{v?.toFixed(1)}</Text> } },
    { title: '信号', dataIndex: 'signal', key: 'signal', render: (v: string) => v === 'buy' ? <Tag color="green">买入</Tag> : v === 'watch' ? <Tag color="orange">关注</Tag> : v === 'extended' ? <Tag color="default">已延伸</Tag> : <Tag>--</Tag> },
    { title: 'RS 排名', dataIndex: 'rs_rating', key: 'rs_rating', render: (v: number) => v ? <Text strong>{v}/99</Text> : '--' },
    { title: '第二阶段', dataIndex: 'trend_passed', key: 'trend_passed', render: (v: boolean) => v ? <Tag color="green">通过</Tag> : <Tag color="red">未通过</Tag> },
  ]

  const signalColumns = [
    { title: '代码', dataIndex: 'symbol', key: 'symbol' },
    { title: '名称', dataIndex: 'name', key: 'name', render: (v: string) => v ? v : <Text type="secondary">--</Text> },
    { title: '类型', dataIndex: 'signal_type', key: 'signal_type', render: (v: string) => <Tag color={v === 'BUY' ? 'green' : 'red'}>{v === 'BUY' ? '买入' : '卖出'}</Tag> },
    { title: '方向', dataIndex: 'direction', key: 'direction' },
    { title: '价格', dataIndex: 'price', key: 'price', render: (v: number) => `$${v?.toFixed(2)}` },
    { title: '状态', dataIndex: 'status', key: 'status' },
  ]

  return (
    <div>
      <Title level={4}>今日仪表盘</Title>

      {/* Market Phase & Stats */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="市场阶段"
              value={dashboard?.market_phase === 'bull' ? '牛市' : dashboard?.market_phase === 'bear' ? '熊市' : '震荡'}
              prefix={dashboard?.market_phase === 'bull' ? <RiseOutlined /> : <FallOutlined />}
              valueStyle={{ color: dashboard?.market_phase === 'bull' ? '#00b96b' : dashboard?.market_phase === 'bear' ? '#ff4d4f' : '#faad14' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="扫描股票" value={dashboard?.total_stocks_scanned || 0} prefix={<TeamOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="第二阶段" value={dashboard?.stage2_passed || 0} prefix={<StockOutlined />} valueStyle={{ color: '#00b96b' }} />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic title="形态识别" value={dashboard?.patterns_found || 0} prefix={<FundOutlined />} valueStyle={{ color: '#00b96b' }} />
          </Card>
        </Col>
      </Row>

      {/* Funnel */}
      <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
        <Col xs={24} md={12}>
          <Card title="今日扫描漏斗">
            <div className="funnel-step">
              <Text>全市场扫描</Text>
              <Text strong>{dashboard?.total_stocks_scanned || 0}</Text>
            </div>
            <div className="funnel-step">
              <Text>→ 第二阶段趋势</Text>
              <Text strong style={{ color: '#00b96b' }}>{dashboard?.stage2_passed || 0}</Text>
            </div>
            <div className="funnel-step">
              <Text>→ RS 排名前 20%</Text>
              <Text strong style={{ color: '#00b96b' }}>{dashboard?.rs_passed || 0}</Text>
            </div>
            <div className="funnel-step">
              <Text>→ 基本面通过</Text>
              <Text strong style={{ color: '#00b96b' }}>{dashboard?.fundamental_passed || 0}</Text>
            </div>
            <div className="funnel-step">
              <Text>→ 形态识别</Text>
              <Text strong style={{ color: '#00b96b' }}>{dashboard?.patterns_found || 0}</Text>
            </div>
            <div className="funnel-step">
              <Text>→ Pivot 附近</Text>
              <Text strong style={{ color: '#faad14' }}>{dashboard?.near_pivot || 0}</Text>
            </div>
          </Card>
        </Col>
        <Col xs={24} md={12}>
          <Card title="今日信号">
            <Row gutter={16}>
              <Col span={12}>
                <Statistic
                  title="买入信号"
                  value={signals?.filter(s => s.signal_type === 'BUY').length || 0}
                  prefix={<ArrowUpOutlined />}
                  valueStyle={{ color: '#00b96b' }}
                />
              </Col>
              <Col span={12}>
                <Statistic
                  title="卖出信号"
                  value={signals?.filter(s => s.signal_type === 'SELL').length || 0}
                  prefix={<ArrowDownOutlined />}
                  valueStyle={{ color: '#ff4d4f' }}
                />
              </Col>
            </Row>
          </Card>
        </Col>
      </Row>

      {/* Tables */}
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="最新选股结果">
            <Table
              dataSource={screenResults?.slice(0, 10) || []}
              columns={columns}
              rowKey="symbol"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="今日信号">
            <Table
              dataSource={signals || []}
              columns={signalColumns}
              rowKey="id"
              size="small"
              pagination={false}
            />
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Dashboard
