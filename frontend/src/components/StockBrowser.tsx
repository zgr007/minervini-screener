import React, { useState, useCallback, useEffect, useRef } from 'react'
import {
  Card, Input, List, Button, Tag, Typography, Space, message, Spin, Empty, Segmented,
  Divider, Row, Col, Tooltip, Popconfirm,
} from 'antd'
import {
  SearchOutlined, PlusCircleOutlined, DeleteOutlined, ReloadOutlined,
  CheckCircleOutlined, LoadingOutlined, StockOutlined,
} from '@ant-design/icons'
import {
  searchStocks, addTrackedStock, removeTrackedStock, getTrackedStocks,
  type StockSearchResult, type TrackedStock,
} from '../services/api'

const { Text, Title } = Typography

const StockBrowser: React.FC = () => {
  // Market mode: US or CN
  const [market, setMarket] = useState<string>('CN')

  // Search state
  const [query, setQuery] = useState('')
  const [searchResults, setSearchResults] = useState<StockSearchResult[]>([])
  const [searching, setSearching] = useState(false)
  const [showResults, setShowResults] = useState(false)
  const searchTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const searchRef = useRef<HTMLDivElement>(null)

  // Tracked stocks
  const [tracked, setTracked] = useState<TrackedStock[]>([])
  const [loadingTracked, setLoadingTracked] = useState(true)

  // Adding state per symbol
  const [adding, setAdding] = useState<Record<string, boolean>>({})

  // Load tracked stocks
  const loadTracked = useCallback(async () => {
    setLoadingTracked(true)
    try {
      const res = await getTrackedStocks(market)
      setTracked(res.data.data || [])
    } catch {
      message.error('加载跟踪列表失败')
    }
    setLoadingTracked(false)
  }, [market])

  useEffect(() => {
    loadTracked()
  }, [loadTracked])

  // Click outside search results to close
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
    setQuery(value)
    if (searchTimer.current) clearTimeout(searchTimer.current)

    if (!value || value.trim().length < 1) {
      setSearchResults([])
      setShowResults(false)
      return
    }

    searchTimer.current = setTimeout(async () => {
      setSearching(true)
      setShowResults(true)
      try {
        const res = await searchStocks(value.trim(), market, 30)
        setSearchResults(res.data.data || [])
      } catch {
        setSearchResults([])
      }
      setSearching(false)
    }, 300)
  }

  // Add a stock
  const handleAdd = async (stock: StockSearchResult) => {
    const key = `${stock.market}:${stock.code}`
    setAdding(prev => ({ ...prev, [key]: true }))
    try {
      await addTrackedStock(stock.code, stock.market, stock.name)
      message.success(`${stock.code} (${stock.name}) 已添加并开始下载数据`)
      setAdding(prev => ({ ...prev, [key]: false }))
      setShowResults(false)
      setQuery('')
      setSearchResults([])
      loadTracked()
    } catch {
      message.error(`添加 ${stock.code} 失败`)
      setAdding(prev => ({ ...prev, [key]: false }))
    }
  }

  // Remove a stock
  const handleRemove = async (stock: TrackedStock) => {
    try {
      await removeTrackedStock(stock.market, stock.symbol)
      message.success(`${stock.symbol} 已移除`)
      loadTracked()
    } catch {
      message.error(`移除 ${stock.symbol} 失败`)
    }
  }

  // Check if a stock is already tracked
  const isTracked = (code: string) => tracked.some(t => t.symbol === code)

  // Market tab color
  const marketColor = market === 'US' ? '#00b96b' : '#1677ff'
  const marketLabel = market === 'US' ? '美股' : 'A股'

  return (
    <Card
      title={
        <Space>
          <StockOutlined />
          <span>添加股票</span>
        </Space>
      }
    >
      {/* Market Toggle */}
      <div style={{ marginBottom: 20 }}>
        <Segmented
          value={market}
          onChange={(val) => {
            setMarket(val as string)
            setQuery('')
            setSearchResults([])
            setShowResults(false)
          }}
          options={[
            { label: '🇨🇳 A股 (CN)', value: 'CN' },
            { label: '🇺🇸 美股 (US)', value: 'US' },
          ]}
          block
          size="large"
        />
      </div>

      {/* Search Section */}
      <div ref={searchRef} style={{ position: 'relative', marginBottom: 24 }}>
        <Input
          size="large"
          placeholder={market === 'CN'
            ? `输入股票代码或名称搜索A股，如 000001 或 平安银行`
            : `输入美股代码搜索，如 AAPL`
          }
          prefix={searching ? <LoadingOutlined /> : <SearchOutlined />}
          value={query}
          onChange={e => handleSearch(e.target.value)}
          onFocus={() => query.trim().length > 0 && setShowResults(true)}
          allowClear
          style={{ borderRadius: 8 }}
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
              maxHeight: 380,
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
                    query.trim().length > 0
                      ? `未找到匹配 "${query}" 的${marketLabel}股票`
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
                const addKey = `${item.market}:${item.code}`
                const isAdding = adding[addKey]
                const alreadyTracked = isTracked(item.code)
                return (
                  <List.Item
                    style={{
                      padding: '8px 12px',
                      cursor: 'pointer',
                      borderRadius: 4,
                      transition: 'background 0.15s',
                    }}
                    onMouseEnter={e => (e.currentTarget.style.background = '#f5f5f5')}
                    onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                    actions={[
                      <Button
                        type="link"
                        size="small"
                        icon={isAdding ? <Spin /> : alreadyTracked ? <CheckCircleOutlined /> : <PlusCircleOutlined />}
                        disabled={alreadyTracked || isAdding}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleAdd(item)
                        }}
                        style={{ minWidth: 60 }}
                      >
                        {isAdding ? '添加中' : alreadyTracked ? '已添加' : '添加'}
                      </Button>,
                    ]}
                  >
                    <List.Item.Meta
                      title={
                        <Space>
                          <Text code strong style={{ fontSize: 14 }}>{item.code}</Text>
                          <Text strong>{item.name}</Text>
                          {item.sector && (
                            <Tag color="blue" style={{ marginLeft: 8 }}>{item.sector}</Tag>
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

      <Divider plain>
        <Space>
          <Text type="secondary">当前跟踪列表</Text>
          <Tag color={marketColor}>{tracked.length} 只</Tag>
        </Space>
      </Divider>

      {/* Tracked Stocks List */}
      <Spin spinning={loadingTracked}>
        {tracked.length === 0 ? (
          <div style={{ padding: '32px 0' }}>
            <Empty description={`暂无${marketLabel}，使用上方搜索框添加`} />
          </div>
        ) : (
          <Row gutter={[8, 8]}>
            {tracked.map(stock => (
              <Col xs={24} sm={12} md={8} lg={6} key={stock.symbol}>
                <Card
                  size="small"
                  style={{
                    borderLeft: `3px solid ${marketColor}`,
                    borderRadius: 6,
                  }}
                  hoverable
                >
                  <Row align="middle" justify="space-between">
                    <Col>
                      <Space direction="vertical" size={0}>
                        <Text strong style={{ fontSize: 16 }}>{stock.symbol}</Text>
                        <Text
                          type={stock.name !== stock.symbol ? 'secondary' : 'danger'}
                          style={{ fontSize: 12 }}
                        >
                          {stock.name !== stock.symbol
                            ? stock.name
                            : '名称待解析'}
                        </Text>
                      </Space>
                    </Col>
                    <Col>
                      <Popconfirm
                        title={`移除 ${stock.symbol}？`}
                        description="将从数据库删除该股票的所有数据"
                        onConfirm={() => handleRemove(stock)}
                        okText="移除"
                        cancelText="取消"
                        okButtonProps={{ danger: true }}
                      >
                        <Tooltip title="移除股票">
                          <Button
                            type="text"
                            danger
                            size="small"
                            icon={<DeleteOutlined />}
                          />
                        </Tooltip>
                      </Popconfirm>
                    </Col>
                  </Row>
                </Card>
              </Col>
            ))}
          </Row>
        )}
      </Spin>

      <Divider />

      <Row justify="space-between" align="middle">
        <Col>
          <Text type="secondary" style={{ fontSize: 12 }}>
            搜索数据来源：{market === 'CN' ? '新浪财经 (AKShare)' : 'Yahoo Finance'}
          </Text>
        </Col>
        <Col>
          <Button icon={<ReloadOutlined />} size="small" onClick={loadTracked} loading={loadingTracked}>
            刷新列表
          </Button>
        </Col>
      </Row>
    </Card>
  )
}

export default StockBrowser
