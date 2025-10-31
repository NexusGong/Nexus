import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

export function formatDate(date: string | Date): string {
  let d: Date
  
  if (typeof date === 'string') {
    // 如果字符串没有时区信息，假设是UTC时间
    if (!date.includes('Z') && !date.includes('+') && !date.includes('-', 10)) {
      // 添加UTC时区标识
      d = new Date(date + 'Z')
    } else {
      d = new Date(date)
    }
  } else {
    d = date
  }
  
  // 检查是否是有效的日期
  if (isNaN(d.getTime())) {
    return '无效日期'
  }
  
  // 获取用户本地时区
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone
  
  // 转换为用户本地时间进行日期比较
  const localD = new Date(d.toLocaleString('en-US', { timeZone: userTimezone }))
  const localNow = new Date(new Date().toLocaleString('en-US', { timeZone: userTimezone }))
  
  const isToday = localD.toDateString() === localNow.toDateString()
  const isYesterday = (() => {
    const yesterday = new Date(localNow)
    yesterday.setDate(yesterday.getDate() - 1)
    return localD.toDateString() === yesterday.toDateString()
  })()
  
  // 获取格式化的日期和时间
  const formattedDate = d.toLocaleDateString('zh-CN', {
    month: 'short',
    day: 'numeric',
    timeZone: userTimezone
  })
  
  const formattedTime = d.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: userTimezone
  })
  
  // 如果是今天
  if (isToday) {
    return `${formattedDate} ${formattedTime}`
  }
  
  // 如果是昨天
  if (isYesterday) {
    return `${formattedDate} ${formattedTime}`
  }
  
  // 其他情况显示完整日期
  return d.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    timeZone: userTimezone
  })
}

export function formatTime(date: string | Date): string {
  let d: Date
  
  if (typeof date === 'string') {
    // 如果字符串没有时区信息，假设是UTC时间
    if (!date.includes('Z') && !date.includes('+') && !date.includes('-', 10)) {
      // 添加UTC时区标识
      d = new Date(date + 'Z')
    } else {
      d = new Date(date)
    }
  } else {
    d = date
  }
  
  // 获取用户本地时区
  const userTimezone = Intl.DateTimeFormat().resolvedOptions().timeZone
  
  return d.toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: userTimezone
  })
}

export function downloadFile(blob: Blob, filename: string) {
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(url)
}

export function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) {
    return navigator.clipboard.writeText(text)
  } else {
    // 降级方案
    const textArea = document.createElement('textarea')
    textArea.value = text
    document.body.appendChild(textArea)
    textArea.focus()
    textArea.select()
    try {
      document.execCommand('copy')
    } catch (err) {
      console.error('复制失败:', err)
    }
    document.body.removeChild(textArea)
    return Promise.resolve()
  }
}

