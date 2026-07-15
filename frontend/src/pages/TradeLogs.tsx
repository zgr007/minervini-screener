import React from 'react'
import { Card, Table, Tag, Typography, Spin } from 'antd'

const { Title, Text } = Typography

const TradeLogs: React.FC = () => {
  // Placeholder - will use real data from API
  const columns = [
    { title: '时间', dataIndex: 'trade_time', key: 'trade_time' },
    { title: '股票', dataIndex: 'symbol', key: 'symbol' },
    { title: '方向', dataIndex: 'side', key: 'side', render: (v: string) => <Tag color={v === 'BUY' ? 'green' : 'red'}>{v === 'BUY' ? '买入' : '卖出'}</Tag> },
    { title: '数量', dataIndex: 'quantity', key: 'quantity' },
    { title: '价格', dataIndex: 'price', key: 'price', render: (v: number) => `$${v?.toFixed(2)}` },
    { title: '费用', dataIndex: 'fee', key: 'fee', render: (v: number) => `$${v?.toFixed(2)}` },
    { title: '备注', dataIndex: 'note', key: 'note' },
  ]

  return (
    <div>
      <Title level={4}>交易日志</Title>
      <Card>
        <Table dataSource={[]} columns={columns} rowKey="id" pagination={{ pageSize: 20 }} />
      </Card>
    </div>
  )
}

export default TradeLogs
