"use client"

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Label } from "@/components/ui/label"
import { ArrowLeft, Plus, Trash2, Save } from "lucide-react"
import Link from "next/link"

interface Source {
  id: number
  name: string
  url: string
  type: string
  description?: string
  created_at?: string
  updated_at?: string
  last_fetched_at?: string
}

const defaultPrompt = `你是一个真诚的人。
你对第一性原理，多维度思考，批判性思考，逆向思维，系统理论、行为心理学、群体心理学、传播学、经济学、认知论、演化心理学、生物学、进化论、道家等领域都有深刻的见解。
你同时是专业的开发者。曾经是自动化、机器学习学习专业的学生。
同时也是一个投资者，对查理芒格理论、长期主义有着深刻的理解。
你尊重事实，实事求是。

你对讲故事、人文、可能有启发的文章也感兴趣。

雷点：
1. 你讨厌夸大、煽情、不实信息和隐藏的商业广告（中间插入部分广告可以理解）。
2. 你讨厌逻辑混乱、概念模糊的文章。
3. 你讨厌煽动情绪、制造焦虑、利用人性弱点的"快餐内容"。`

export default function SettingsPage() {
  const [sources, setSources] = useState<Source[]>([])
  const [prompt, setPrompt] = useState("")
  const [newSource, setNewSource] = useState({ name: "", url: "", description: "" })
  const [isLoading, setIsLoading] = useState(true)
  const [isSaving, setIsSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [successMessage, setSuccessMessage] = useState<string | null>(null)

  // 获取后端API地址
  const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://43.139.154.191:8000'

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setIsLoading(true)
      setError(null)
      
      // 并行获取订阅源和提示词
      const [sourcesRes, promptRes] = await Promise.all([
        fetch(`${API_BASE}/api/sources`),
        fetch(`${API_BASE}/api/settings/prompt`)
      ])

      if (!sourcesRes.ok) {
        throw new Error(`获取订阅源失败: ${sourcesRes.status}`)
      }
      if (!promptRes.ok) {
        throw new Error(`获取提示词失败: ${promptRes.status}`)
      }

      const sourcesData = await sourcesRes.json()
      const promptData = await promptRes.json()

      setSources(sourcesData)
      setPrompt(promptData.prompt || defaultPrompt)
    } catch (err) {
      console.error('加载数据失败:', err)
      setError(err instanceof Error ? err.message : '加载数据失败')
      // 如果API调用失败，使用默认提示词
      setPrompt(defaultPrompt)
    } finally {
      setIsLoading(false)
    }
  }

  const handleDeleteSource = async (id: number) => {
    try {
      setError(null)
      setSuccessMessage(null)
      
      console.log(`正在删除订阅源 ID: ${id}`)
      console.log(`API URL: ${API_BASE}/api/sources/${id}`)
      
      const response = await fetch(`${API_BASE}/api/sources/${id}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      })

      console.log(`删除响应状态: ${response.status}`)
      
      if (!response.ok) {
        const errorText = await response.text()
        console.error('删除错误响应:', errorText)
        
        let errorData
        try {
          errorData = JSON.parse(errorText)
        } catch {
          errorData = { detail: errorText }
        }
        
        throw new Error(errorData.detail || `删除失败: ${response.status}`)
      }

      const result = await response.json()
      console.log('删除成功:', result)

      // 成功删除后更新UI
      setSources((prev) => prev.filter((source) => source.id !== id))
      setSuccessMessage('订阅源已删除')
      
      // 3秒后清除成功消息
      setTimeout(() => setSuccessMessage(null), 3000)
      
    } catch (err) {
      console.error('删除订阅源失败:', err)
      setError(err instanceof Error ? err.message : '删除订阅源失败')
    }
  }

  const handleAddSource = async () => {
    if (!newSource.name || !newSource.url) return

    try {
      const response = await fetch(`${API_BASE}/api/sources`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          name: newSource.name,
          url: newSource.url,
          type: 'RSS'
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `添加失败: ${response.status}`)
      }

      const newSourceData = await response.json()
      
      setSources((prev) => [...prev, { ...newSourceData }])
      setNewSource({ name: "", url: "", description: "" })
    } catch (err) {
      console.error('添加订阅源失败:', err)
      setError(err instanceof Error ? err.message : '添加订阅源失败')
    }
  }

  const handleSavePrompt = async () => {
    try {
      setIsSaving(true)
      setError(null)

      const response = await fetch(`${API_BASE}/api/settings/prompt`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          prompt: prompt
        }),
      })

      if (!response.ok) {
        const errorData = await response.json()
        throw new Error(errorData.detail || `保存失败: ${response.status}`)
      }

      // 可以添加成功提示
      console.log('提示词保存成功')
    } catch (err) {
      console.error('保存提示词失败:', err)
      setError(err instanceof Error ? err.message : '保存提示词失败')
    } finally {
      setIsSaving(false)
    }
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

      {error && (
        <div className="max-w-3xl mx-auto mb-6">
          <div className="bg-destructive/10 border border-destructive/20 text-destructive px-4 py-3 rounded flex items-center justify-between">
            <span>{error}</span>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => setError(null)}
              className="h-auto p-1 text-destructive hover:text-destructive"
            >
              ×
            </Button>
          </div>
        </div>
      )}

      {successMessage && (
        <div className="max-w-3xl mx-auto mb-6">
          <div className="bg-green-50 border border-green-200 text-green-800 px-4 py-3 rounded flex items-center justify-between">
            <span>{successMessage}</span>
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={() => setSuccessMessage(null)}
              className="h-auto p-1 text-green-800 hover:text-green-800"
            >
              ×
            </Button>
          </div>
        </div>
      )}

      <main className="max-w-3xl mx-auto grid gap-6 sm:gap-8 md:grid-cols-2">
        <Card className="bg-card border-border shadow-lg shadow-stone-200/20">
          <CardHeader>
            <CardTitle className="text-lg font-light text-foreground">订阅源</CardTitle>
          </CardHeader>
          <CardContent className="space-y-5">
            <div className="space-y-3 max-h-96 overflow-y-auto pr-2">
              {sources.map((source) => (
                <div key={source.id} className="p-4 bg-secondary/50 rounded-md border border-border/50">
                  <div className="flex items-center justify-between mb-1.5">
                    <h3 className="font-medium text-foreground text-sm">{source.name}</h3>
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
                  {source.description && <p className="text-xs text-muted-foreground mb-1">{source.description}</p>}
                  <p className="text-xs text-accent-foreground/70 font-mono break-all">{source.url}</p>
                </div>
              ))}
              {sources.length === 0 && (
                <p className="text-center text-muted-foreground text-sm py-8">
                  暂无订阅源，请添加新源
                </p>
              )}
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
