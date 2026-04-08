/**
 * 异步任务API使用示例
 *
 * 展示如何在前端使用新的异步API：
 * 1. 提交任务，立即获取task_id
 * 2. 轮询任务状态
 * 3. 获取最终结果
 */

// API基础URL
const API_BASE = 'http://localhost:8000';

/**
 * 提交综述生成任务
 */
async function submitReviewTask(params) {
  const response = await fetch(`${API_BASE}/api/smart-generate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(params),
  });

  const result = await response.json();

  if (!result.success) {
    throw new Error(result.message);
  }

  return result.data; // { task_id, topic, status, poll_url }
}

/**
 * 查询任务状态
 */
async function getTaskStatus(taskId) {
  const response = await fetch(`${API_BASE}/api/tasks/${taskId}`);
  const result = await response.json();

  if (!result.success) {
    throw new Error(result.message);
  }

  return result.data; // { task_id, topic, status, progress, result?, error? }
}

/**
 * 轮询任务直到完成
 */
async function pollTaskUntilComplete(taskId, options = {}) {
  const {
    onProgress = (status, progress) => console.log(status, progress),
    pollInterval = 1000, // 1秒
    maxPolls = 300,      // 最多5分钟
  } = options;

  let pollCount = 0;

  while (pollCount < maxPolls) {
    const taskInfo = await getTaskStatus(taskId);

    // 调用进度回调
    onProgress(taskInfo.status, taskInfo.progress);

    // 检查是否完成
    if (taskInfo.status === 'completed') {
      return {
        success: true,
        data: taskInfo.result,
        pollCount,
      };
    }

    // 检查是否失败
    if (taskInfo.status === 'failed') {
      return {
        success: false,
        error: taskInfo.error,
        pollCount,
      };
    }

    // 等待后继续轮询
    await new Promise(resolve => setTimeout(resolve, pollInterval));
    pollCount++;
  }

  throw new Error('轮询超时');
}

/**
 * 完整使用示例
 */
async function generateReviewExample() {
  try {
    // 1. 提交任务
    console.log('提交综述生成任务...');
    const taskData = await submitReviewTask({
      topic: '基于FMEA法的Agent开发项目风险管理研究',
      target_count: 50,
      recent_years_ratio: 0.5,
      english_ratio: 0.3,
      search_years: 10,
      max_search_queries: 8,
    });

    console.log('任务已提交:', taskData);
    const { task_id } = taskData;

    // 2. 轮询任务状态
    console.log('开始轮询任务状态...');

    const result = await pollTaskUntilComplete(task_id, {
      onProgress: (status, progress) => {
        const message = progress?.message || status;
        console.log(`[${status}] ${message}`);
      },
    });

    // 3. 处理结果
    if (result.success) {
      console.log('综述生成成功!');
      console.log('论文数量:', result.data.cited_papers_count);
      console.log('统计信息:', result.data.statistics);

      // 显示综述内容
      console.log('综述预览:', result.data.review?.substring(0, 200) + '...');
    } else {
      console.error('综述生成失败:', result.error);
    }

  } catch (error) {
    console.error('错误:', error.message);
  }
}

/**
 * React Hook 示例
 */
function useReviewGeneration() {
  const [taskId, setTaskId] = React.useState(null);
  const [status, setStatus] = React.useState('idle');
  const [progress, setProgress] = React.useState({});
  const [result, setResult] = React.useState(null);
  const [error, setError] = React.useState(null);

  const submitTask = async (params) => {
    setStatus('submitting');
    setError(null);

    try {
      const taskData = await submitReviewTask(params);
      setTaskId(taskData.task_id);
      setStatus('polling');
    } catch (err) {
      setError(err.message);
      setStatus('error');
    }
  };

  React.useEffect(() => {
    let intervalId = null;

    if (status === 'polling' && taskId) {
      intervalId = setInterval(async () => {
        try {
          const taskInfo = await getTaskStatus(taskId);
          setProgress(taskInfo.progress || {});

          if (taskInfo.status === 'completed') {
            setStatus('completed');
            setResult(taskInfo.result);
            clearInterval(intervalId);
          } else if (taskInfo.status === 'failed') {
            setStatus('error');
            setError(taskInfo.error);
            clearInterval(intervalId);
          }
        } catch (err) {
          setError(err.message);
          setStatus('error');
          clearInterval(intervalId);
        }
      }, 1000);
    }

    return () => {
      if (intervalId) clearInterval(intervalId);
    };
  }, [status, taskId]);

  return {
    status,
    progress,
    result,
    error,
    submitTask,
  };
}

// 使用React Hook的组件示例
function ReviewGenerator() {
  const { status, progress, result, error, submitTask } = useReviewGeneration();

  const handleSubmit = () => {
    submitTask({
      topic: document.getElementById('topic').value,
      target_count: 50,
      recent_years_ratio: 0.5,
      english_ratio: 0.3,
    });
  };

  return (
    <div>
      <input id="topic" placeholder="输入论文主题" />
      <button onClick={handleSubmit} disabled={status === 'polling'}>
        {status === 'polling' ? '生成中...' : '生成综述'}
      </button>

      {status === 'polling' && (
        <div>
          <p>进度: {progress.message || '处理中...'}</p>
        </div>
      )}

      {status === 'completed' && (
        <div>
          <h3>生成成功!</h3>
          <p>论文数量: {result.cited_papers_count}</p>
          <div>{result.review}</div>
        </div>
      )}

      {status === 'error' && (
        <div>
          <p style={{color: 'red'}}>错误: {error}</p>
        </div>
      )}
    </div>
  );
}

// 导出函数供使用
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    submitReviewTask,
    getTaskStatus,
    pollTaskUntilComplete,
    generateReviewExample,
  };
}
