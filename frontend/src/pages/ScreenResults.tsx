import React, { useEffect, useRef, useState } from 'react'
import {
  Table, Tag, Typography, Spin, Tooltip, Button, Progress, Space, message,
} from 'antd'
import { PlayCircleOutlined, ReloadOutlined } from '@ant-design/icons'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { getScreenResults, runScreen, getScanProgress } from '../services/api'
import type { ScreenResult, ScanProgress } from '../services/types'

const { Title, Text } = Typography

const ScreenResults: React.FC = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const [scanning, setScanning] = useState(false)
  const [progress, setProgress] = useState<ScanProgress | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['screen-results'],
    queryFn: () => getScreenResults().then(r => r.data.data),
  })

  const results = data as ScreenResult[] | undefined

  // Poll progress while scan is running
  useEffect(() => {
    if (!scanning) return
    pollRef.current = setInterval(async () => {
      try {
        const res = await getScanProgress()
        const p = res.data.data as ScanProgress
        setProgress(p)
        if (p.status === 'completed') {
          setScanning(false)
          setProgress(null)
          message.success('扫描完成！')
          queryClient.invalidateQueries({ queryKey: ['screen-results'] })
          queryClient.invalidateQueries({ queryKey: ['dashboard'] })
          clearInterval(pollRef.current!)
          pollRef.current = null
        } else if (p.status === 'failed') {
          setScanning(false)
          message.error(`扫描失败: ${p.message}`)
          clearInterval(pollRef.current!)
          pollRef.current = null
        }
      } catch {
        // ignore polling errors
      }
    }, 2000)
    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
    }
  }, [scanning, queryClient])

  const handleRunScan = async () => {
    setScanning(true)
    setProgress({
      run_id: null,
      status: 'running',
      phase: 'starting',
      phase_label: '启动中...',
      total: 0,
      processed: 0,
      percent: 0,
      message: '',
      started_at: null,
      completed_at: null,
    })
    try {
      const res = await runScreen('CN')
      // Polling will pick up progress via the useEffect above
    } catch {
      message.error('启动扫描失败')
      setScanning(false)
      setProgress(null)
    }
  }

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
      {/* Header with Run Scan button */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <Title level={4} style={{ margin: 0 }}>选股结果</Title>
        <Space>
          <Button
            icon={<ReloadOutlined />}
            onClick={() => queryClient.invalidateQueries({ queryKey: ['screen-results'] })}
          >
            刷新
          </Button>
          <Button
            type="primary"
            icon={scanning ? <Spin /> : <PlayCircleOutlined />}
            onClick={handleRunScan}
            disabled={scanning}
            size="large"
          >
            {scanning ? '扫描中...' : '开始扫描'}
          </Button>
        </Space>
      </div>

      {/* Progress Bar */}
      {scanning && progress && (
        <div style={{
          marginBottom: 16,
          padding: '8px 12px',
          background: 'linear-gradient(90deg, #e6f4ff 0%, #f6ffed 100%)',
          borderRadius: 8,
        }}>
          <Space direction="vertical" style={{ width: '100%' }} size={4}>
            <Space>
              <Text strong style={{ fontSize: 13 }}>
                {progress.status === 'running' ? progress.phase_label : ''}
              </Text>
              <Text style={{ fontSize: 12, color: '#666' }}>
                {progress.processed > 0
                  ? `${progress.processed} / ${progress.total}`
                  : ''}
              </Text>
              {progress.message && (
                <Text style={{ fontSize: 11, color: '#999' }}>
                  {progress.message}
                </Text>
              )}
            </Space>
            <Progress
              percent={progress.percent}
              status={progress.status === 'failed' ? 'exception' : 'active'}
              strokeColor={{
                '0%': '#1677ff',
                '100%': '#00b96b',
              }}
              format={(pct) => `${pct?.toFixed(1)}%`}
            />
          </Space>
        </div>
      )}

      {/* Results Table */}
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
