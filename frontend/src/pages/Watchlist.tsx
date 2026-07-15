import React from 'react'
import { Table, Card, Tag, Typography, Space, Spin, Button, Tooltip } from 'antd'
import { PlusOutlined, DeleteOutlined, EditOutlined } from '@ant-design/icons'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getWatchlist } from '../services/api'
import type { WatchlistItem } from '../services/types'

const { Title, Text } = Typography

const statusMap: Record<string, { color: string; text: string }> = {
  watching: { color: 'default', text: '观察中' },
  near_pivot: { color: 'orange', text: '接近买点' },
  triggered: { color: 'green', text: '已触发' },
  expired: { color: 'red', text: '已失效' },
  bought: { color: 'blue', text: '已买入' },
}

const Watchlist: React.FC = () => {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['watchlist'],
    queryFn: () => getWatchlist().then(r => r.data.data),
  })

  const items = data as WatchlistItem[] | undefined

  const columns = [
    {
      title: '股票代码',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (v: string) => <a onClick={() => navigate(`/stock/${v}`)}>{v}</a>,
    },
    {
      title: '加入日期',
      dataIndex: 'added_date',
      key: 'added_date',
      render: (v: string) => v ? new Date(v).toLocaleDateString() : '--',
    },
    {
      title: '来源',
      dataIndex: 'source',
      key: 'source',
      render: (v: string | null) => v ? <Tag>{v === 'SCREEN' ? '选股' : '手动'}</Tag> : '--',
    },
    {
      title: 'Pivot 价格',
      dataIndex: 'pivot_price',
      key: 'pivot_price',
      render: (v: number | null) => v ? `$${v.toFixed(2)}` : '--',
    },
    {
      title: '止损价',
      dataIndex: 'stop_price',
      key: 'stop_price',
      render: (v: number | null) => v ? `$${v.toFixed(2)}` : '--',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => {
        const s = statusMap[v] || { color: 'default', text: v }
        return <Tag color={s.color}>{s.text}</Tag>
      },
    },
    {
      title: '备注',
      dataIndex: 'note',
      key: 'note',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'actions',
      render: () => (
        <Space>
          <Tooltip title="编辑"><Button size="small" icon={<EditOutlined />} /></Tooltip>
          <Tooltip title="移除"><Button size="small" danger icon={<DeleteOutlined />} /></Tooltip>
        </Space>
      ),
    },
  ]

  if (isLoading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>观察列表</Title>
        <Button type="primary" icon={<PlusOutlined />}>添加股票</Button>
      </div>
      <Card>
        <Table
          dataSource={items || []}
          columns={columns}
          rowKey="id"
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </div>
  )
}

export default Watchlist
