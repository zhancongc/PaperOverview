/**
 * David 数据统计页面
 * 展示访问数、注册数、生成数、付费数等统计信息
 */
import React, { useState, useEffect } from 'react';

interface OverviewStats {
  visits: {
    total: number;
    today: number;
  };
  registers: {
    total: number;
    today: number;
  };
  generations: {
    total: number;
    free: number;
    paid: number;
  };
  payments: {
    total_orders: number;
    total_revenue: number;
    by_plan: {
      [key: string]: {
        name: string;
        count: number;
        revenue: number;
      };
    };
  };
  today: {
    today_visits: number;
    today_registers: number;
    today_generations: number;
    today_payments: number;
    today_revenue: number;
  };
}

interface DailyStats {
  date: string;
  visits: number;
  registers: number;
  generations: number;
  payments: number;
  revenue: number;
}

export const DavidPage: React.FC = () => {
  const [overview, setOverview] = useState<OverviewStats | null>(null);
  const [dailyStats, setDailyStats] = useState<DailyStats[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [days, setDays] = useState(30);

  useEffect(() => {
    fetchStats();
  }, [days]);

  const fetchStats = async () => {
    try {
      setLoading(true);
      setError(null);

      // 获取概览数据
      const overviewRes = await fetch('/api/admin/stats/overview');
      if (!overviewRes.ok) throw new Error('获取概览数据失败');
      const overviewData = await overviewRes.json();
      setOverview(overviewData.data);

      // 获取每日数据
      const dailyRes = await fetch(`/api/admin/stats/daily?days=${days}`);
      if (!dailyRes.ok) throw new Error('获取每日数据失败');
      const dailyData = await dailyRes.json();
      setDailyStats(dailyData.data.stats);

    } catch (err) {
      setError(err instanceof Error ? err.message : '加载数据失败');
    } finally {
      setLoading(false);
    }
  };

  const formatNumber = (num: number) => {
    return new Intl.NumberFormat('zh-CN').format(num);
  };

  const formatCurrency = (num: number) => {
    return new Intl.NumberFormat('zh-CN', {
      style: 'currency',
      currency: 'CNY'
    }).format(num);
  };

  const StatCard: React.FC<{
    title: string;
    value: string | number;
    subtitle?: string;
    color?: string;
  }> = ({ title, value, subtitle, color = 'blue' }) => (
    <div className="stat-card">
      <div className="stat-title">{title}</div>
      <div className={`stat-value stat-${color}`}>{value}</div>
      {subtitle && <div className="stat-subtitle">{subtitle}</div>}
    </div>
  );

  if (loading) {
    return (
      <div className="david-page">
        <div className="loading-container">
          <div className="spinner"></div>
          <p>加载数据中...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="david-page">
        <div className="error-container">
          <p>{error}</p>
          <button onClick={fetchStats} className="retry-btn">重试</button>
        </div>
      </div>
    );
  }

  if (!overview) {
    return null;
  }

  return (
    <div className="david-page">
      <div className="david-container">
        <header className="david-header">
          <h1>数据统计中心</h1>
          <p className="david-subtitle">实时监控系统运营数据</p>
        </header>

        {/* 概览卡片 */}
        <section className="david-section">
          <h2 className="section-title">数据概览</h2>
          <div className="stats-grid">
            <StatCard
              title="总访问量"
              value={formatNumber(overview.visits.total)}
              subtitle={`今日 +${formatNumber(overview.visits.today)}`}
              color="blue"
            />
            <StatCard
              title="总注册量"
              value={formatNumber(overview.registers.total)}
              subtitle={`今日 +${formatNumber(overview.registers.today)}`}
              color="green"
            />
            <StatCard
              title="总生成数"
              value={formatNumber(overview.generations.total)}
              subtitle={`免费 ${formatNumber(overview.generations.free)} | 付费 ${formatNumber(overview.generations.paid)}`}
              color="purple"
            />
            <StatCard
              title="总收入"
              value={formatCurrency(overview.payments.total_revenue)}
              subtitle={`共 ${overview.payments.total_orders} 笔订单`}
              color="orange"
            />
          </div>
        </section>

        {/* 今日数据 */}
        <section className="david-section">
          <h2 className="section-title">今日数据</h2>
          <div className="today-grid">
            <div className="today-item">
              <span className="today-label">访问量</span>
              <span className="today-value">{formatNumber(overview.today.today_visits)}</span>
            </div>
            <div className="today-item">
              <span className="today-label">注册量</span>
              <span className="today-value">{formatNumber(overview.today.today_registers)}</span>
            </div>
            <div className="today-item">
              <span className="today-label">生成数</span>
              <span className="today-value">{formatNumber(overview.today.today_generations)}</span>
            </div>
            <div className="today-item">
              <span className="today-label">付费数</span>
              <span className="today-value">{formatNumber(overview.today.today_payments)}</span>
            </div>
            <div className="today-item">
              <span className="today-label">收入</span>
              <span className="today-value today-revenue">{formatCurrency(overview.today.today_revenue)}</span>
            </div>
          </div>
        </section>

        {/* 套餐统计 */}
        <section className="david-section">
          <h2 className="section-title">套餐统计</h2>
          <div className="plans-grid">
            {Object.entries(overview.payments.by_plan).map(([type, data]: [string, any]) => (
              <div key={type} className="plan-card">
                <div className="plan-name">{data.name}</div>
                <div className="plan-stats">
                  <div className="plan-stat">
                    <span className="plan-label">订单数</span>
                    <span className="plan-number">{formatNumber(data.count)}</span>
                  </div>
                  <div className="plan-stat">
                    <span className="plan-label">收入</span>
                    <span className="plan-number plan-revenue">{formatCurrency(data.revenue)}</span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </section>

        {/* 每日趋势 */}
        <section className="david-section">
          <div className="trend-header">
            <h2 className="section-title">每日趋势</h2>
            <div className="days-selector">
              <button
                className={`days-btn ${days === 7 ? 'active' : ''}`}
                onClick={() => setDays(7)}
              >7天</button>
              <button
                className={`days-btn ${days === 30 ? 'active' : ''}`}
                onClick={() => setDays(30)}
              >30天</button>
              <button
                className={`days-btn ${days === 90 ? 'active' : ''}`}
                onClick={() => setDays(90)}
              >90天</button>
            </div>
          </div>

          <div className="trend-table-container">
            <table className="trend-table">
              <thead>
                <tr>
                  <th>日期</th>
                  <th>访问量</th>
                  <th>注册量</th>
                  <th>生成数</th>
                  <th>付费数</th>
                  <th>收入</th>
                </tr>
              </thead>
              <tbody>
                {dailyStats.map((day) => (
                  <tr key={day.date}>
                    <td>{day.date}</td>
                    <td>{formatNumber(day.visits)}</td>
                    <td>{formatNumber(day.registers)}</td>
                    <td>{formatNumber(day.generations)}</td>
                    <td>{formatNumber(day.payments)}</td>
                    <td className="trend-revenue">{formatCurrency(day.revenue)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>

      <style>{`
        .david-page {
          min-height: 100vh;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 40px 20px;
        }

        .david-container {
          max-width: 1200px;
          margin: 0 auto;
        }

        .david-header {
          text-align: center;
          color: white;
          margin-bottom: 40px;
        }

        .david-header h1 {
          font-size: 2.5rem;
          font-weight: 700;
          margin-bottom: 10px;
        }

        .david-subtitle {
          font-size: 1.1rem;
          opacity: 0.9;
        }

        .david-section {
          background: white;
          border-radius: 16px;
          padding: 30px;
          margin-bottom: 30px;
          box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }

        .section-title {
          font-size: 1.5rem;
          font-weight: 600;
          margin-bottom: 25px;
          color: #333;
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: 20px;
        }

        .stat-card {
          padding: 25px;
          border-radius: 12px;
          background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        }

        .stat-title {
          font-size: 0.9rem;
          color: #666;
          margin-bottom: 10px;
        }

        .stat-value {
          font-size: 2rem;
          font-weight: 700;
          margin-bottom: 8px;
        }

        .stat-blue { color: #2196F3; }
        .stat-green { color: #4CAF50; }
        .stat-purple { color: #9C27B0; }
        .stat-orange { color: #FF9800; }

        .stat-subtitle {
          font-size: 0.85rem;
          color: #888;
        }

        .today-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
          gap: 15px;
        }

        .today-item {
          text-align: center;
          padding: 20px;
          background: #f8f9fa;
          border-radius: 10px;
        }

        .today-label {
          display: block;
          font-size: 0.9rem;
          color: #666;
          margin-bottom: 8px;
        }

        .today-value {
          display: block;
          font-size: 1.5rem;
          font-weight: 600;
          color: #333;
        }

        .today-revenue {
          color: #4CAF50;
        }

        .plans-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
          gap: 15px;
        }

        .plan-card {
          padding: 20px;
          background: linear-gradient(135deg, #e0eafe 0%, #f0f4ff 100%);
          border-radius: 10px;
        }

        .plan-name {
          font-size: 1.1rem;
          font-weight: 600;
          color: #333;
          margin-bottom: 15px;
        }

        .plan-stats {
          display: flex;
          justify-content: space-between;
        }

        .plan-stat {
          text-align: center;
        }

        .plan-label {
          display: block;
          font-size: 0.8rem;
          color: #666;
          margin-bottom: 5px;
        }

        .plan-number {
          display: block;
          font-size: 1.1rem;
          font-weight: 600;
          color: #333;
        }

        .plan-revenue {
          color: #4CAF50;
        }

        .trend-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
          margin-bottom: 20px;
        }

        .days-selector {
          display: flex;
          gap: 10px;
        }

        .days-btn {
          padding: 8px 20px;
          border: 1px solid #ddd;
          background: white;
          border-radius: 6px;
          cursor: pointer;
          transition: all 0.2s;
        }

        .days-btn:hover {
          background: #f5f5f5;
        }

        .days-btn.active {
          background: #2196F3;
          color: white;
          border-color: #2196F3;
        }

        .trend-table-container {
          overflow-x: auto;
        }

        .trend-table {
          width: 100%;
          border-collapse: collapse;
        }

        .trend-table th,
        .trend-table td {
          padding: 12px 15px;
          text-align: left;
          border-bottom: 1px solid #eee;
        }

        .trend-table th {
          background: #f8f9fa;
          font-weight: 600;
          color: #666;
        }

        .trend-table tbody tr:hover {
          background: #f8f9fa;
        }

        .trend-revenue {
          color: #4CAF50;
          font-weight: 600;
        }

        .loading-container,
        .error-container {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
          color: white;
        }

        .spinner {
          width: 50px;
          height: 50px;
          border: 4px solid rgba(255,255,255,0.3);
          border-top-color: white;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }

        .retry-btn {
          margin-top: 20px;
          padding: 12px 30px;
          background: white;
          color: #667eea;
          border: none;
          border-radius: 8px;
          cursor: pointer;
          font-weight: 600;
        }

        @media (max-width: 768px) {
          .david-header h1 {
            font-size: 1.8rem;
          }

          .stats-grid {
            grid-template-columns: 1fr;
          }

          .today-grid {
            grid-template-columns: repeat(2, 1fr);
          }

          .trend-header {
            flex-direction: column;
            gap: 15px;
            align-items: flex-start;
          }
        }
      `}</style>
    </div>
  );
};
