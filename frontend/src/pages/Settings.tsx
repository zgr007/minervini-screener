import React, { useEffect, useState, useCallback, useRef } from 'react'
import { Card, Form, InputNumber, Switch, Select, Typography, Button, Divider, message, Tabs, Row, Col, Statistic, Tag, Spin, Space } from 'antd'
import { SaveOutlined, CloudDownloadOutlined, CheckCircleOutlined, CloseCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import { getDataStatus, updateData, getDataUpdateStatus } from '../services/api'
import StockBrowser from '../components/StockBrowser'

const { Title, Text } = Typography

const Settings: React.FC = () => {
  const [form] = Form.useForm()

  const onSave = () => {
    message.success('配置已保存')
  }

  return (
    <div>
      <Title level={4}>系统设置</Title>
      <Tabs defaultActiveKey="screening">
        <Tabs.TabPane tab="选股参数" key="screening">
          <Card>
            <Form form={form} layout="vertical" initialValues={{
              rs_threshold: 80, near_high_15pct: 15, min_fundamental: 6,
              volume_multiplier: 1.5, max_risk: 2, max_single_position: 25,
            }}>
              <Form.Item label="RS 最低百分位" name="rs_threshold">
                <InputNumber min={1} max={99} style={{ width: 200 }} />
              </Form.Item>
              <Form.Item label="距 52 周新高阈值 (%)" name="near_high_15pct">
                <InputNumber min={1} max={50} style={{ width: 200 }} />
              </Form.Item>
              <Form.Item label="基本面最低分" name="min_fundamental">
                <InputNumber min={0} max={10} style={{ width: 200 }} />
              </Form.Item>
              <Form.Item label="成交量放大倍数" name="volume_multiplier">
                <InputNumber min={1} max={5} step={0.1} style={{ width: 200 }} />
              </Form.Item>
              <Form.Item label="单笔最大风险 (%)" name="max_risk">
                <InputNumber min={0.5} max={5} step={0.5} style={{ width: 200 }} />
              </Form.Item>
              <Form.Item label="单只股票仓位上限 (%)" name="max_single_position">
                <InputNumber min={5} max={50} style={{ width: 200 }} />
              </Form.Item>
              <Button type="primary" icon={<SaveOutlined />} onClick={onSave}>保存设置</Button>
            </Form>
          </Card>
        </Tabs.TabPane>
        <Tabs.TabPane tab="通知配置" key="notifications">
          <Card>
            <Form layout="vertical">
              <Form.Item label="飞书 Webhook">
                <InputNumber style={{ width: 400 }} placeholder="Webhook URL" />
              </Form.Item>
              <Form.Item label="Telegram Bot Token">
                <InputNumber style={{ width: 400 }} placeholder="Bot Token" />
              </Form.Item>
              <Form.Item label="启用邮件通知">
                <Switch />
              </Form.Item>
              <Form.Item label="启用 Bark">
                <Switch />
              </Form.Item>
            </Form>
          </Card>
        </Tabs.TabPane>
        <Tabs.TabPane tab="风控参数" key="risk">
          <Card>
            <Form layout="vertical" initialValues={{ bull_max: 100, neutral_max: 60, bear_max: 20 }}>
              <Form.Item label="牛市总仓位上限 (%)" name="bull_max">
                <InputNumber min={0} max={100} style={{ width: 200 }} />
              </Form.Item>
              <Form.Item label="震荡市总仓位上限 (%)" name="neutral_max">
                <InputNumber min={0} max={100} style={{ width: 200 }} />
              </Form.Item>
              <Form.Item label="熊市总仓位上限 (%)" name="bear_max">
                <InputNumber min={0} max={100} style={{ width: 200 }} />
              </Form.Item>
            </Form>
          </Card>
        </Tabs.TabPane>
        <Tabs.TabPane tab="数据管理" key="data">
          <DataManagement />
        </Tabs.TabPane>
        <Tabs.TabPane tab="添加股票" key="stock-browser">
          <StockBrowser />
        </Tabs.TabPane>
      </Tabs>
    </div>
  )
}


const DataManagement: React.FC = () => {
  const [status, setStatus] = useState<{
    last_update: Record<string, string | null>
    has_data: Record<string, boolean>
    stock_counts: Record<string, number>
  }>({ last_update: {}, has_data: {}, stock_counts: {} })
  const [loading, setLoading] = useState(false)
  const [downloading, setDownloading] = useState<Record<string, boolean>>({})
  const pollRef = useRef<Record<string, ReturnType<typeof setInterval>>>({})

  const loadStatus = useCallback(async () => {
    setLoading(true)
    try {
      const res = await getDataStatus()
      setStatus(res.data.data)
    } catch {
      // ignore
    }
    setLoading(false)
  }, [])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  const startUpdate = async (market: string) => {
    setDownloading(prev => ({ ...prev, [market]: true }))
    try {
      const res = await updateData(market)
      const taskId = res.data.data.task_id
      message.loading({ content: `${market === 'US' ? '美股' : 'A股'}数据更新中...`, key: taskId })

      // Poll for completion
      pollRef.current[market] = setInterval(async () => {
        try {
          const taskRes = await getDataUpdateStatus(taskId)
          const task = taskRes.data.data
          if (task.status === 'completed') {
            clearInterval(pollRef.current[market])
            message.success({ content: `${market === 'US' ? '美股' : 'A股'}数据更新完成`, key: taskId })
            setDownloading(prev => ({ ...prev, [market]: false }))
            loadStatus()
          } else if (task.status === 'failed') {
            clearInterval(pollRef.current[market])
            message.error({ content: `${market === 'US' ? '美股' : 'A股'}更新失败: ${task.error || '未知错误'}`, key: taskId, duration: 5 })
            setDownloading(prev => ({ ...prev, [market]: false }))
          }
        } catch {
          clearInterval(pollRef.current[market])
          message.error({ content: `${market} 状态查询失败`, key: taskId })
          setDownloading(prev => ({ ...prev, [market]: false }))
        }
      }, 2000)
    } catch {
      message.error(`${market === 'US' ? '美股' : 'A股'}更新启动失败`)
      setDownloading(prev => ({ ...prev, [market]: false }))
    }
  }

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      Object.values(pollRef.current).forEach(clearInterval)
    }
  }, [])

  const marketConfigs = [
    { key: 'US', label: '美股 (US)', color: '#00b96b' },
    { key: 'CN', label: 'A股 (CN)', color: '#1677ff' },
  ]

  return (
    <div>
      <Row gutter={[24, 24]}>
        {marketConfigs.map(m => {
          const lastUpdate = status.last_update?.[m.key]
          const hasData = status.has_data?.[m.key]
          const stockCount = status.stock_counts?.[m.key] ?? 0
          const isDownloading = downloading[m.key]

          return (
            <Col xs={24} md={12} key={m.key}>
              <Card
                title={
                  <Space>
                    <span style={{ color: m.color, fontWeight: 'bold' }}>{m.label}</span>
                    {hasData
                      ? <Tag icon={<CheckCircleOutlined />} color="success">已配置</Tag>
                      : <Tag icon={<CloseCircleOutlined />} color="default">未下载</Tag>
                    }
                  </Space>
                }
                extra={
                  <Button
                    type="primary"
                    icon={isDownloading ? <Spin /> : <CloudDownloadOutlined />}
                    onClick={() => startUpdate(m.key)}
                    disabled={isDownloading}
                    loading={isDownloading}
                  >
                    {isDownloading ? '更新中...' : '更新数据'}
                  </Button>
                }
              >
                <Row gutter={[16, 16]}>
                  <Col span={12}>
                    <Statistic title="股票数量" value={stockCount} suffix="只" />
                  </Col>
                  <Col span={12}>
                    <Statistic
                      title="最后更新"
                      value={lastUpdate ? lastUpdate.slice(0, 10) : '--'}
                      valueStyle={{ fontSize: 16 }}
                    />
                  </Col>
                </Row>
                {!hasData && (
                  <div style={{ marginTop: 12 }}>
                    <Text type="secondary">尚未下载数据，点击"更新数据"按钮开始下载</Text>
                  </div>
                )}
              </Card>
            </Col>
          )
        })}
      </Row>

      <Divider />

      <Row gutter={[16, 16]}>
        <Col>
          <Button icon={<ReloadOutlined />} onClick={loadStatus} loading={loading}>
            刷新状态
          </Button>
        </Col>
      </Row>
    </div>
  )
}

export default Settings
