'use client'

import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'

export default function TestPage() {
  const [htmlContent, setHtmlContent] = useState('')
  const [displayContent, setDisplayContent] = useState('')

  const handleDisplay = () => {
    setDisplayContent(htmlContent)
  }

  const handleClear = () => {
    setHtmlContent('')
    setDisplayContent('')
  }

  return (
    <div className="container mx-auto p-6 space-y-6">
      <div className="text-center">
        <h1 className="text-3xl font-bold">HTML 测试页面</h1>
        <p className="text-muted-foreground mt-2">粘贴 HTML 内容并查看渲染效果</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 输入区域 */}
        <Card>
          <CardHeader>
            <CardTitle>HTML 输入</CardTitle>
            <CardDescription>在下方粘贴你的 HTML body 内容</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="html-input">HTML 内容</Label>
              <Textarea
                id="html-input"
                placeholder="请在这里粘贴你的 HTML 内容..."
                value={htmlContent}
                onChange={(e) => setHtmlContent(e.target.value)}
                className="min-h-[300px] font-mono text-sm"
              />
            </div>
            <div className="flex gap-2">
              <Button onClick={handleDisplay} disabled={!htmlContent.trim()}>
                显示内容
              </Button>
              <Button variant="outline" onClick={handleClear}>
                清空
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 显示区域 */}
        <Card>
          <CardHeader>
            <CardTitle>渲染结果</CardTitle>
            <CardDescription>HTML 内容的渲染效果</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border rounded-md p-4 min-h-[300px] bg-background">
              {displayContent ? (
                <div
                  dangerouslySetInnerHTML={{ __html: displayContent }}
                  className="prose prose-sm max-w-none"
                />
              ) : (
                <div className="text-muted-foreground text-center py-12">
                  粘贴 HTML 内容并点击"显示内容"按钮查看渲染效果
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* 全屏显示区域 */}
      {displayContent && (
        <Card>
          <CardHeader>
            <CardTitle>全屏预览</CardTitle>
            <CardDescription>完整的渲染效果</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="border rounded-md p-6 bg-background">
              <div
                dangerouslySetInnerHTML={{ __html: displayContent }}
                className="prose max-w-none"
              />
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
