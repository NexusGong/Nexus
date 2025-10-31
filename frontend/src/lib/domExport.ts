import html2canvas from 'html2canvas'

export async function exportOpenDialogAsPng(filename = 'analysis_card.png', scale = 2): Promise<void> {
  const dialog = document.querySelector('[role="dialog"][data-state="open"]') as HTMLElement | null
  if (!dialog) throw new Error('未找到打开的对话框')

  const canvas = await html2canvas(dialog, {
    scale,
    backgroundColor: '#ffffff',
    useCORS: true,
    logging: false,
    windowWidth: dialog.scrollWidth,
    windowHeight: dialog.scrollHeight,
    ignoreElements: (el) => {
      // 忽略关闭按钮、导出按钮区域等不必要控件
      const className = (el as HTMLElement).className || ''
      if (typeof className === 'string' && (
        className.includes('absolute right-4 top-4') ||
        className.includes('DialogFooter')
      )) return true
      return false
    }
  })

  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (!blob) return reject(new Error('导出失败'))
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
      resolve()
    }, 'image/png')
  })
}



