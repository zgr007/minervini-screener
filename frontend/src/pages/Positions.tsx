import React from 'react'
import { Card, Table, Tag, Typography, Spin } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { getPositions } from '../services/api'
import type { Position } from '../services/types'

const { Title, Text } = Typography

const Positions: React.FC = () => {
  const { data, isLoading } = useQuery({
    queryKey: ['positions'],
    queryFn: () => getPositions().then(r => r.data.data),
  })

  const positions = data as Position[] | undefined

  const columns = [
    { title: '股票', dataIndex: 'symbol', key: 'symbol' },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    {
      title: '均价',
      dataIndex: 'average_cost',
      key: 'average_cost',
      render: (v: number) => `$${v?.toFixed(2)}`,
    },
    {
      title: '现价',
      dataIndex: 'current_price',
      key: 'current_price',
      render: (v: number | undefined) => v ? `$${v.toFixed(2)}` : '--',
    },
    {
      title: '盈亏',
      key: 'pnl',
      render: (_: unknown, record: Position) => {
        if (!record.current_price) return '--'
        const pnl = (record.current_price - record.average_cost) * record.quantity
        const pnlPct = ((record.current_price - record.average_cost) / record.average_cost) * 100
        return (
          <Text style={{ color: pnl >= 0 ? '#00b96b' : '#ff4d4f' }}>
            ${pnl.toFixed(2)} ({pnlPct.toFixed(2)}%)
          </Text>
        )
      },
    },
    {
      title: '止损价',
      dataIndex: 'current_stop',
      key: 'current_stop',
      render: (v: number | null) => v ? `$${v.toFixed(2)}` : '--',
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      render: (v: string) => <Tag color={v === 'open' ? 'green' : 'default'}>{v === 'open' ? '持仓中' : '已平仓'}</Tag>,
    },
    {
      title: '开仓日',
      dataIndex: 'opened_at',
      key: 'opened_at',
      render: (v: string | null) => v ? new Date(v).toLocaleDateString() : '--',
    },
  ]

  if (isLoading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  const openPositions = positions?.filter(p => p.status === 'open') || []
  const closedPositions = positions?.filter(p => p.status === 'closed') || []

  return (
    <div>
      <Title level={4}>持仓管理</Title>
      <Card title={`当前持仓 (${openPositions.length})`} style={{ marginBottom: 16 }}>
        <Table dataSource={openPositions} columns={columns} rowKey="id" pagination={false} />
      </Card>
      <Card title={`历史持仓 (${closedPositions.length})`}>
        <Table dataSource={closedPositions} columns={columns} rowKey="id" pagination={{ pageSize: 10 }} />
      </Card>
    </div>
  )
}

export default Positions
