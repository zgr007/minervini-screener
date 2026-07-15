import React, { useState, useRef, useEffect } from 'react'
import { Card, Form, InputNumber, Select, DatePicker, Button, Table, Typography, Row, Col, Statistic, Alert, Space, Tag, Input, List, Spin, Empty, message, Drawer, Divider } from 'antd'
import { PlayCircleOutlined, ImportOutlined, ReloadOutlined, SearchOutlined, PlusCircleOutlined, CheckCircleOutlined, LoadingOutlined } from '@ant-design/icons'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { getBacktests, runBacktest, searchStocks, getScreenResults } from '../services/api'
import type { BacktestResult, BacktestMetrics } from '../services/types'
import type { StockSearchResult } from '../services/api'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

const Backtest: React.FC = () => {
  const [form] = Form.useForm()
  const [selectedSymbols, setSelectedSymbols] = useState<string[]>([])
  const queryClient = useQueryClient()

  // === Stock Search (like StockBrowser) ===
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const searchRef = useRef<HTMLDivElement>(null)

  // Click outside to close search results
  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowResults(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  // Debounced search
  const handleSearch = (value: string) => {
    setSearchQuery(value)
    if (searchTimer.current) clearTimeout(searchTimer.current)

    if (!value || value.trim().length < 1) {
      setSearchResults([])
      setShowResults(false)
      return
    }

    const mkt = form.getFieldValue('market') || 'US'
    searchTimer.current = setTimeout(async () => {
      setSearching(true)
      setShowResults(true)
      try {
        const res = await searchStocks(value.trim(), mkt, 30, true)
        setSearchResults(res.data.data || [])
      } catch {
        setSearchResults([])
      }
      setSearching(false)
    }, 300)
  }

  // Add stock to pool
  const addToPool = (code: string) => {
    if (!selectedSymbols.includes(code)) {
      setSelectedSymbols(prev => [...prev, code])
    }
  }

  // Remove stock from pool
  const removeFromPool = (code: string) => {
    setSelectedSymbols(prev => prev.filter(s => s !== code))
  }

  // Import stocks from screening results
  const importFromScreen = async () => {
    try {
      const res = await getScreenResults()
      const results = (res.data as any)?.data ?? res.data ?? []
      const symbols: string[] = Array.isArray(results)
        ? results.map((r: any) => r.symbol).filter(Boolean)
        : []
      if (symbols.length) {
        setSelectedSymbols(symbols)
        message.success(`已导入 ${symbols.length} 只股票`)
      } else {
        message.warning('选股结果为空')
      }
    } catch {
      message.error('导入失败')
    }
  }

  const currentMarket = Form.useWatch('market', form) || 'US'
  const marketLabel = currentMarket === 'US' ? '美股' : 'A股'

  // === Backtest data & execution ===
  const { data, isLoading, error } = useQuery({
    queryKey: ['backtests'],
    queryFn: () => getBacktests().then(r => r.data.data),
    retry: 1,
  })

  const backtests = data as BacktestResult[] | undefined

  // Detail drawer state
  const [detailItem, setDetailItem] = useState<BacktestResult | null>(null)

  const mutation = useMutation({
    mutationFn: (values: any) => runBacktest(values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['backtests'] })
    },
  })

  const onRun = (values: any) => {
    mutation.mutate({
      market: values.market,
      start_date: values.dateRange?.[0]?.format('YYYY-MM-DD'),
      end_date: values.dateRange?.[1]?.format('YYYY-MM-DD'),
      initial_capital: values.initial_capital || 100000,
      commission_pct: values.commission_pct || 0.001,
      slippage_pct: values.slippage_pct || 0.001,
      symbols: selectedSymbols.length ? selectedSymbols : undefined,
    })
  }

  const renderMetrics = (metrics: BacktestMetrics) => (
    <Row gutter={[16, 16]}>
      <Col xs={12} sm={6}><Statistic title="总收益率" value={metrics.total_return} suffix="%" precision={2} valueStyle={{ color: metrics.total_return >= 0 ? '#00b96b' : '#ff4d4f' }} /></Col>
      <Col xs={12} sm={6}><Statistic title="年化收益" value={metrics.cagr} suffix="%" precision={2} /></Col>
      <Col xs={12} sm={6}><Statistic title="夏普比率" value={metrics.sharpe} precision={2} /></Col>
      <Col xs={12} sm={6}><Statistic title="最大回撤" value={metrics.max_drawdown} suffix="%" precision={2} valueStyle={{ color: '#ff4d4f' }} /></Col>
      <Col xs={12} sm={6}><Statistic title="胜率" value={metrics.win_rate} suffix="%" precision={1} /></Col>
      <Col xs={12} sm={6}><Statistic title="交易次数" value={metrics.total_trades} /></Col>
      <Col xs={12} sm={6}><Statistic title="盈亏比" value={metrics.profit_factor} precision={2} /></Col>
      <Col xs={12} sm={6}><Statistic title="平均持仓" value={metrics.avg_holding_days} suffix="天" /></Col>
    </Row>
  )

  const resultColumns = [
    { title: '市场', dataIndex: ['config', 'market'], key: 'market', width: 60 },
    { title: '开始', dataIndex: ['config', 'start_date'], key: 'start_date', width: 100 },
    { title: '结束', dataIndex: ['config', 'end_date'], key: 'end_date', width: 100 },
    { title: '股票池', dataIndex: ['config', 'symbols'], key: 'symbols', width: 200, render: (v: string[] | null) => v?.length ? (() => {
      const show = v.slice(0, 3)
      const rest = v.length - 3
      return (
        <Space size={4}>
          {show.map(s => <Tag key={s} style={{ fontSize: 12 }}>{s}</Tag>)}
          {rest > 0 && <Text type="secondary">+{rest}</Text>}
        </Space>
      )
    })() : <Text type="secondary">全市场</Text> },
    { title: '收益率', dataIndex: ['metrics', 'total_return'], key: 'total_return', width: 80, render: (v: number) => v != null ? `${v.toFixed(2)}%` : '--' },
    { title: '夏普', dataIndex: ['metrics', 'sharpe'], key: 'sharpe', width: 70, render: (v: number) => v != null ? v.toFixed(2) : '--' },
    { title: '回撤', dataIndex: ['metrics', 'max_drawdown'], key: 'max_drawdown', width: 80, render: (v: number) => v != null ? `${v.toFixed(2)}%` : '--' },
    { title: '胜率', dataIndex: ['metrics', 'win_rate'], key: 'win_rate', width: 70, render: (v: number) => v != null ? `${v.toFixed(1)}%` : '--' },
  ]

  // Run result (mutation response may be flat or nested)
  const runResult: BacktestMetrics | null = mutation.data
    ? (mutation.data as any)?.metrics ?? (mutation.data as any)?.data?.metrics ?? (mutation.data as any)?.data?.data?.metrics ?? null
    : null

  // Extract message from response (e.g. "没有可用的股票数据")
  const runMessage: string | null = mutation.data
    ? (mutation.data as any)?.message ?? (mutation.data as any)?.data?.message ?? null
    : null

  return (
    <div>
      <Title level={4}>回测系统</Title>

      {error && !isLoading && (
        <Alert message="加载历史回测失败" type="warning" showIcon style={{ marginBottom: 16 }} closable />
      )}

      <Card title="回测参数" style={{ marginBottom: 16 }}>
        <Form form={form} layout="vertical" onFinish={onRun} initialValues={{ market: 'US', initial_capital: 100000, commission_pct: 0.001, slippage_pct: 0.001 }}>
          <Row gutter={16}>
            <Col span={4}>
              <Form.Item name="market" label="市场">
                <Select style={{ width: '100%' }}>
                  <Select.Option value="US">美股</Select.Option>
                  <Select.Option value="CN">A股</Select.Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={6}>
              <Form.Item name="dateRange" label="时间范围">
                <RangePicker style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item name="initial_capital" label="初始资金">
                <InputNumber min={10000} max={10000000} step={10000} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={3}>
              <Form.Item name="commission_pct" label="手续费">
                <InputNumber min={0} max={0.01} step={0.0001} style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={3}>
              <Form.Item label=" " colon={false}>
                <Button type="primary" htmlType="submit" icon={<PlayCircleOutlined />} loading={mutation.isPending} block>
                  运行
                </Button>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16} style={{ marginTop: 8 }}>
            <Col span={16}>
              <div style={{ marginBottom: 4 }}>
                <Text>自定义股票池（选填，留空=全市场扫描）</Text>
              </div>
              <div ref={searchRef} style={{ position: 'relative' }}>
                <Input
                  placeholder={`输入代码或名称搜索${marketLabel}并添加，留空=全市场`}
                  prefix={searching ? <LoadingOutlined /> : <SearchOutlined />}
                  value={searchQuery}
                  onChange={e => handleSearch(e.target.value)}
                  onFocus={() => searchQuery.trim().length > 0 && setShowResults(true)}
                  allowClear
                  size="middle"
                  style={{ borderRadius: 6 }}
                />

                {/* Search Results Dropdown */}
                {showResults && (
                  <Card
                    style={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      zIndex: 1000,
                      maxHeight: 360,
                      overflow: 'auto',
                      boxShadow: '0 6px 16px rgba(0,0,0,0.12)',
                      borderRadius: 8,
                      marginTop: 4,
                    }}
                    styles={{ body: { padding: 4 } }}
                  >
                    {searchResults.length === 0 && !searching && (
                      <div style={{ padding: '20px 0' }}>
                        <Empty
                          description={
                            searchQuery.trim().length > 0
                              ? `未找到匹配 "${searchQuery}" 的${marketLabel}`
                              : '输入关键词开始搜索'
                          }
                        />
                      </div>
                    )}

                    {searching && (
                      <div style={{ textAlign: 'center', padding: 16 }}>
                        <Spin size="small" /> <Text style={{ marginLeft: 8 }}>搜索中...</Text>
                      </div>
                    )}

                    <List
                      dataSource={searchResults}
                      renderItem={(item) => {
                        const alreadyAdded = selectedSymbols.includes(item.code)
                        return (
                          <List.Item
                            style={{
                              padding: '6px 12px',
                              cursor: 'pointer',
                              borderRadius: 4,
                              transition: 'background 0.15s',
                            }}
                            onMouseEnter={e => (e.currentTarget.style.background = '#f5f5f5')}
                            onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                            onClick={() => {
                              if (!alreadyAdded) {
                                addToPool(item.code)
                                setSearchQuery('')
                                setSearchResults([])
                                setShowResults(false)
                              }
                            }}
                            actions={[
                              <Button
                                type="link"
                                size="small"
                                icon={alreadyAdded ? <CheckCircleOutlined /> : <PlusCircleOutlined />}
                                disabled={alreadyAdded}
                                style={{ minWidth: 50 }}
                              >
                                {alreadyAdded ? '已添加' : '添加'}
                              </Button>,
                            ]}
                          >
                            <List.Item.Meta
                              title={
                                <Space>
                                  <Text code strong style={{ fontSize: 14 }}>{item.code}</Text>
                                  <Text strong>{item.name}</Text>
                                  {item.sector && (
                                    <Tag color="blue" style={{ marginLeft: 4 }}>{item.sector}</Tag>
                                  )}
                                </Space>
                              }
                            />
                          </List.Item>
                        )
                      }}
                    />
                  </Card>
                )}
              </div>

              {/* Selected Stocks Tags */}
              {selectedSymbols.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <Space size={[4, 4]} wrap>
                    {selectedSymbols.map(sym => (
                      <Tag
                        key={sym}
                        closable
                        onClose={() => removeFromPool(sym)}
                        style={{ fontSize: 13, padding: '2px 8px' }}
                      >
                        {sym}
                      </Tag>
                    ))}
                  </Space>
                  <Text type="secondary" style={{ marginLeft: 8, fontSize: 12 }}>
                    {selectedSymbols.length} 只
                  </Text>
                </div>
              )}
            </Col>
            <Col span={4}>
              <Form.Item label=" " colon={false}>
                <Button icon={<ImportOutlined />} onClick={importFromScreen} block>
                  从选股导入
                </Button>
              </Form.Item>
            </Col>
            <Col span={4}>
              <Form.Item label=" " colon={false}>
                <Button icon={<ReloadOutlined />} onClick={() => { setSelectedSymbols([]); setSearchQuery(''); }} block>
                  清空
                </Button>
              </Form.Item>
            </Col>
          </Row>
        </Form>
      </Card>

      {mutation.isPending && (
        <Card style={{ marginBottom: 16, textAlign: 'center' }}>
          <Text type="secondary">回测运行中，请耐心等待...</Text>
        </Card>
      )}

      {mutation.isError && (
        <Alert message="回测执行失败" description={String((mutation.error as any)?.message || mutation.error)} type="error" showIcon style={{ marginBottom: 16 }} closable />
      )}

      {runMessage && runResult?.total_trades === 0 && (
        <Alert message={runMessage} type="warning" showIcon style={{ marginBottom: 16 }} closable />
      )}

      {runResult && (
        <Card title="回测结果" style={{ marginBottom: 16 }}>
          {renderMetrics(runResult)}
        </Card>
      )}

      <Card title="历史回测" loading={isLoading}>
        <Table
          dataSource={backtests || []}
          columns={resultColumns}
          rowKey="id"
          size="small"
          pagination={{ pageSize: 10, showTotal: (t) => `共 ${t} 条` }}
          locale={{ emptyText: '暂无回测记录，点击"运行"开始第一次回测' }}
          onRow={(record) => ({
            onDoubleClick: () => setDetailItem(record as BacktestResult),
            style: { cursor: 'pointer' },
          })}
        />
      </Card>

      {/* Detail Drawer */}
      <Drawer
        title={detailItem ? `回测详情 — ${detailItem.id}` : ''}
        placement="right"
        width={640}
        open={!!detailItem}
        onClose={() => setDetailItem(null)}
      >
        {detailItem && (
          <>
            <div style={{ marginBottom: 8 }}>
              <Text type="secondary">
                {detailItem.config.start_date} → {detailItem.config.end_date}
                {' | '}市场: {detailItem.config.market}
                {detailItem.config.symbols?.length ? ` | 股票池: ${detailItem.config.symbols.join(', ')}` : ' | 全市场'}
                {' | '}初始资金: ¥{detailItem.config.initial_capital?.toLocaleString()}
              </Text>
            </div>

            <Divider />
            <Title level={5}>指标</Title>
            {renderMetrics(detailItem.metrics)}

            <Divider />
            <Title level={5}>交易明细 ({detailItem.trades?.length || 0} 笔)</Title>
            <Table
              dataSource={detailItem.trades || []}
              columns={[
                { title: '代码', dataIndex: 'symbol', key: 'symbol', width: 70 },
                { title: '买入', dataIndex: 'entry_date', key: 'entry_date', width: 100 },
                { title: '买入价', dataIndex: 'entry_price', key: 'entry_price', width: 80, render: (v: number) => v?.toFixed(2) },
                { title: '卖出', dataIndex: 'exit_date', key: 'exit_date', width: 100 },
                { title: '卖出价', dataIndex: 'exit_price', key: 'exit_price', width: 80, render: (v: number) => v?.toFixed(2) },
                { title: '盈亏', dataIndex: 'pnl_pct', key: 'pnl_pct', width: 70, render: (v: number) => <Text style={{ color: v >= 0 ? '#00b96b' : '#ff4d4f' }}>{v?.toFixed(2)}%</Text> },
                { title: '原因', dataIndex: 'exit_reason', key: 'exit_reason', width: 70 },
              ]}
              rowKey={(_, i) => String(i)}
              size="small"
              pagination={false}
            />

            <Divider />
            <Title level={5}>净值曲线</Title>
            {detailItem.equity_curve?.length ? (
              <div>
                <Row gutter={16}>
                  <Col span={8}><Statistic title="起始净值" value={detailItem.equity_curve[0]?.value} precision={2} prefix="¥" /></Col>
                  <Col span={8}><Statistic title="最终净值" value={detailItem.equity_curve[detailItem.equity_curve.length - 1]?.value} precision={2} prefix="¥" valueStyle={{ color: detailItem.metrics.total_return >= 0 ? '#00b96b' : '#ff4d4f' }} /></Col>
                  <Col span={8}><Statistic title="最高净值" value={Math.max(...detailItem.equity_curve.map(e => e.value))} precision={2} prefix="¥" /></Col>
                </Row>
                <div style={{ marginTop: 12, maxHeight: 200, overflow: 'auto' }}>
                  <Table
                    dataSource={detailItem.equity_curve.filter((_, i) => i % Math.max(1, Math.floor(detailItem.equity_curve.length / 30)) === 0 || i === detailItem.equity_curve.length - 1)}
                    columns={[
                      { title: '日期', dataIndex: 'date', key: 'date', width: 110 },
                      { title: '净值', dataIndex: 'value', key: 'value', width: 100, render: (v: number) => `¥${v?.toLocaleString()}` },
                    ]}
                    rowKey="date"
                    size="small"
                    pagination={false}
                  />
                </div>
              </div>
            ) : (
              <Text type="secondary">无净值数据</Text>
            )}
          </>
        )}
      </Drawer>
    </div>
  )
}

export default Backtest
