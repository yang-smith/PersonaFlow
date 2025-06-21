"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { Switch } from "@/components/ui/switch"
import { ArrowLeft, Plus, Trash2, Save } from "lucide-react"
import Link from "next/link"

interface Source {
  id: string
  name: string
  url: string
  enabled: boolean
  description?: string
}

// 模拟数据
// const mockSources: Source[] = [
//   {
//     id: "1",
//     name: "哲思月刊",
//     url: "https://philosophy-monthly.com/rss",
//     enabled: true,
//     description: "深度思考与人生哲学",
//   },
//   {
//     id: "2",
//     name: "生活美学",
//     url: "https://lifestyle-aesthetics.com/feed",
//     enabled: true,
//     description: "极简生活与美学思考",
//   },
//   {
//     id: "3",
//     name: "科技人文",
//     url: "https://tech-humanities.com/rss",
//     enabled: false,
//     description: "技术与人文的交汇点",
//   },
// ]

// const defaultPrompt = `你是一位具有深度思考能力的AI助手，专注于为用户筛选和推荐高质量的内容。

// 在评估文章时，请重点关注：
// 1. 思想深度：是否能引发深层思考
// 2. 实用价值：是否对个人成长有帮助
// 3. 文字质量：表达是否清晰优雅
// 4. 独特视角：是否提供新颖的观点

// 请用温和、深思熟虑的语调来撰写推荐理由和摘要，体现出对知识的敬畏和对读者的关怀。`

export default function SettingsPage() {
  const [sources, setSources] = useState<Source[]>([])
  const [prompt, setPrompt] = useState("")
  const [newSource, setNewSource] = useState({ name: "", url: "", description: "" })
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)

  useEffect(() => {
    setTimeout(() => {
      // setSources(mockSources); // Assuming API connected
      // setPrompt(defaultPrompt); // Assuming API connected
      setIsLoading(false)
    }, 500)
  }, [])

  const handleToggleSource = async (id: string) => {
    setSources((prev) => prev.map((source) => (source.id === id ? { ...source, enabled: !source.enabled } : source)))
    // 模拟API调用
    await new Promise((resolve) => setTimeout(resolve, 200))
  }

  const handleDeleteSource = async (id: string) => {
    setSources((prev) => prev.filter((source) => source.id !== id))
    // 模拟API调用
    await new Promise((resolve) => setTimeout(resolve, 200))
  }

  const handleAddSource = async () => {
    if (!newSource.name || !newSource.url) return

    const source: Source = {
      id: Date.now().toString(),
      name: newSource.name,
      url: newSource.url,
      description: newSource.description,
      enabled: true,
    }

    setSources((prev) => [...prev, source])
    setNewSource({ name: "", url: "", description: "" })

    // 模拟API调用
    await new Promise((resolve) => setTimeout(resolve, 200))
  }

  const handleSavePrompt = async () => {
    setIsSaving(true)
    // 模拟API调用
    await new Promise((resolve) => setTimeout(resolve, 1000))
    setIsSaving(false)
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-lg font-light text-muted-foreground animate-pulse">载入设定...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background p-4 sm:p-6">
      <header className="max-w-3xl mx-auto pt-6 pb-8 flex items-center">
        <Link href="/" className="mr-4">
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
            <ArrowLeft className="w-5 h-5" />
          </Button>
        </Link>
        <h1 className="text-2xl sm:text-3xl font-light text-foreground">设定</h1>
      </header>

      <main className="max-w-3xl mx-auto grid gap-6 sm:gap-8 md:grid-cols-2">
        <Card className="bg-card border-border shadow-lg shadow-stone-200/20">
          {" "}
          {/* 卡片样式调整 */}
          <CardHeader>
            <CardTitle className="text-lg font-light text-foreground">订阅源</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
              {" "}
              {/* 增加滚动条 */}
              {sources.map((source) => (
                <div key={source.id} className="p-4 bg-secondary/50 rounded-md border border-border/50">
                  <div className="flex items-center justify-between mb-1.5">
                    <h3 className="font-medium text-foreground text-sm">{source.name}</h3>
                    <Switch
                      checked={source.enabled}
                      onCheckedChange={() => handleToggleSource(source.id)}
                      // Shadcn switch already has good styling, ensure it matches theme
                    />
                  </div>
                  {source.description && <p className="text-xs text-muted-foreground mb-1">{source.description}</p>}
                  <p className="text-xs text-accent-foreground/70 font-mono break-all">{source.url}</p>
                  <div className="text-right mt-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteSource(source.id)}
                      className="text-destructive/70 hover:text-destructive hover:bg-destructive/10 px-2 py-1 h-auto"
                    >
                      <Trash2 className="w-3.5 h-3.5 mr-1" />
                      移除
                    </Button>
                  </div>
                </div>
              ))}
            </div>

            <div className="border-t border-border pt-5 space-y-3">
              <h4 className="font-medium text-foreground text-sm">添加新源</h4>
              <div>
                <Label htmlFor="source-name" className="text-xs text-muted-foreground mb-1 block">
                  名称
                </Label>
                <Input
                  id="source-name"
                  value={newSource.name}
                  onChange={(e) => setNewSource((prev) => ({ ...prev, name: e.target.value }))}
                  placeholder="如：格物志"
                  className="bg-background border-border text-sm"
                />
              </div>
              <div>
                <Label htmlFor="source-url" className="text-xs text-muted-foreground mb-1 block">
                  RSS链接
                </Label>
                <Input
                  id="source-url"
                  value={newSource.url}
                  onChange={(e) => setNewSource((prev) => ({ ...prev, url: e.target.value }))}
                  placeholder="https://example.com/feed"
                  className="bg-background border-border text-sm"
                />
              </div>
              <div>
                <Label htmlFor="source-desc" className="text-xs text-muted-foreground mb-1 block">
                  简介 (可选)
                </Label>
                <Input
                  id="source-desc"
                  value={newSource.description}
                  onChange={(e) => setNewSource((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="此源之简述"
                  className="bg-background border-border text-sm"
                />
              </div>
              <Button
                onClick={handleAddSource}
                disabled={!newSource.name || !newSource.url}
                className="w-full bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
              >
                <Plus className="w-4 h-4 mr-1.5" />
                添入此源
              </Button>
            </div>
          </CardContent>
        </Card>

        <Card className="bg-card border-border shadow-lg shadow-stone-200/20">
          <CardHeader>
            <CardTitle className="text-lg font-light text-foreground">AI人格</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <Label htmlFor="ai-prompt" className="text-xs text-muted-foreground mb-1 block">
                System Prompt
              </Label>
              <Textarea
                id="ai-prompt"
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                rows={10}
                className="bg-background border-border resize-none font-mono text-xs sm:text-sm leading-relaxed"
                placeholder="定义AI之心性与言谈..."
              />
            </div>
            <Button
              onClick={handleSavePrompt}
              disabled={isSaving}
              className="w-full bg-primary text-primary-foreground hover:bg-primary/90 text-sm"
            >
              <Save className="w-4 h-4 mr-1.5" />
              {isSaving ? "存续中..." : "保存心诀"}
            </Button>
          </CardContent>
        </Card>
      </main>

      <footer className="max-w-3xl mx-auto mt-10 py-6 text-center">
        <p className="text-xs text-muted-foreground">格物致知，诚意正心。</p>
      </footer>
    </div>
  )
}
