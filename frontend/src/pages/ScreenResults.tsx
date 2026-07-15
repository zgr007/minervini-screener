import React from 'react'
import { Table, Tag, Typography, Spin, Tooltip } from 'antd'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getScreenResults } from '../services/api'
import type { ScreenResult } from '../services/types'

const { Title, Text } = Typography

const ScreenResults: React.FC = () => {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['screen-results'],
    queryFn: () => getScreenResults().then(r => r.data.data),
  })

  const results = data as ScreenResult[] | undefined

  const columns = [
    {
      title: '代码',
      dataIndex: 'symbol',
      key: 'symbol',
      width: 90,
      render: (v: string) => <a onClick={() => navigate(`/stock/${v}`)}>{v}</a>,
    },
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (v: string, r: ScreenResult) => v && v !== r.symbol ? v : <Text type="secondary">--</Text>,
    },
    {
      title: '评分',
      dataIndex: 'total_score',
      key: 'total_score',
      width: 80,
      sorter: (a: ScreenResult, b: ScreenResult) => b.total_score - a.total_score,
      render: (v: number) => {
        const color = v >= 80 ? '#00b96b' : v >= 60 ? '#faad14' : v > 0 ? '#ff4d4f' : '#999'
        return <Text strong style={{ color }}>{v?.toFixed(1)}</Text>
      },
    },
    {
      title: '信号',
      dataIndex: 'signal',
      key: 'signal',
      width: 70,
                  render: (v: string) => v === 'buy' ? <Tag color="green" style={{ margin: 0 }}>买入</Tag>
                    : v === 'watch' ? <Tag color="orange" style={{ margin: 0 }}>关注</Tag>
                    : v === 'extended' ? <Tag color="default" style={{ margin: 0 }}>已延伸</Tag>
                    : <Tag style={{ margin: 0 }}>--</Tag>,
    },
    {
      title: 'RS',
      dataIndex: 'rs_rating',
      key: 'rs_rating',
      width: 60,
      render: (v: number) => v ? <Text strong>{v}</Text> : '--',
    },
    {
      title: '第二阶段',
      dataIndex: 'trend_passed',
      key: 'trend_passed',
      width: 90,
      render: (v: boolean) => v ? <Tag color="green" style={{ margin: 0 }}>✓ 通过</Tag> : <Tag color="red" style={{ margin: 0 }}>✗</Tag>,
    },
    {
      title: '理由',
      key: 'reason',
      ellipsis: true,
      render: (_: unknown, record: ScreenResult) => {
        const parts: string[] = []
        if (!record.trend_passed) parts.push('非Stage2')
        if (record.rs_rating && record.rs_rating < 80) parts.push(`RS ${record.rs_rating}`)
        if (record.total_score > 0) parts.push(`评分 ${record.total_score}`)
        return (
          <Tooltip title={record.reason ? JSON.stringify(record.reason, null, 2) : ''}>
            <Text style={{ fontSize: 12 }}>
              {record.signal === 'buy' ? '买入信号' : parts.length > 0 ? parts.join('，') : '--'}
            </Text>
          </Tooltip>
        )
      },
    },
  ]

  if (isLoading) {
    return <Spin size="large" style={{ display: 'flex', justifyContent: 'center', marginTop: 100 }} />
  }

  return (
    <div>
      <Title level={4} style={{ marginBottom: 16 }}>选股结果</Title>
      <Table
        dataSource={results || []}
        columns={columns}
        rowKey="symbol"
        scroll={{ x: 'max-content' }}
        pagination={{ pageSize: 20, showTotal: (total) => `共 ${total} 只股票` }}
      />
    </div>
  )
}

export default ScreenResults
