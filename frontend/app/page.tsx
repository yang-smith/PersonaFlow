"use client"

import { useState, useEffect } from "react"
import { Card, CardContent } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Heart, BookOpen, X, Settings } from "lucide-react"
import Link from "next/link"

// API 配置
const API_BASE_URL = "http://localhost:8000"

interface Article {
  id: number
  title: string
  content: string
  ai_summary: string
  ai_rationale: string
  published_at: string
  url: string
  source_name: string
  final_score?: number
}

// 删除模拟数据，改为从API获取
// const mockArticles: Article[] = [...]

export default function FeedPage() {
  const [articles, setArticles] = useState<Article[]>([])
  const [currentArticle, setCurrentArticle] = useState<Article | null>(null)
  const [isReading, setIsReading] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [isTransitioning, setIsTransitioning] = useState(false)
  const [isRevealingNext, setIsRevealingNext] = useState(false)

  // 从后端获取文章数据
  const fetchArticles = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/feed`)
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      const data = await response.json()
      console.log('Fetched articles:', data)
      setArticles(data)
      setCurrentArticle(data[0] || null)
      setIsLoading(false)
    } catch (error) {
      console.error('Failed to fetch articles:', error)
      setIsLoading(false)
      // 可以显示错误状态或使用fallback数据
    }
  }

  useEffect(() => {
    fetchArticles()
  }, [])

  const handleAction = async (action: "like" | "read" | "dislike") => {
    if (!currentArticle || isTransitioning || isRevealingNext) return

    setIsTransitioning(true)

    // 调用后端API
    try {
      const apiAction = action === "dislike" ? "skip" : action === "read" ? "skip" : "like"
      
      const response = await fetch(`${API_BASE_URL}/api/feed/action`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          article_id: currentArticle.id,
          action: apiAction
        })
      })

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }

      const result = await response.json()
      console.log('Action recorded:', result)
    } catch (error) {
      console.error('Failed to record action:', error)
      // 即使API调用失败，也继续前端的状态更新
    }

    const remainingArticles = articles.slice(1)

    if (remainingArticles.length > 0) {
      setTimeout(() => {
        setCurrentArticle(remainingArticles[0])
        setArticles(remainingArticles)
        setIsRevealingNext(true)
      }, 150)
    } else {
      setTimeout(() => {
        setCurrentArticle(null)
        setArticles([])
      }, 800)
    }

    setTimeout(() => {
      setIsTransitioning(false)
      setIsRevealingNext(false)
    }, 900)
  }

  const handleCardClick = () => {
    if (!isTransitioning && !isRevealingNext) {
      setIsReading(true)
    }
  }

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <p className="text-lg font-light text-muted-foreground animate-pulse">静候佳音...</p>
      </div>
    )
  }

  if (!currentArticle && !isTransitioning && !isRevealingNext) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-background p-8 text-center">
        <div className="mb-8">
          <svg
            xmlns="http://www.w3.org/2000/svg"
            width="64"
            height="64"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="text-muted-foreground opacity-50"
          >
            <path d="M12 22a10 10 0 0 0-8.66-5H3.34A10 10 0 0 0 12 22z" />
            <path d="M2 17a10 10 0 0 1 10 5 10 10 0 0 1 10-5" />
            <path d="M12 2v10" />
            <path d="M12 2L6.83 7.17" />
            <path d="M12 2l5.17 5.17" />
          </svg>
        </div>
        <h2 className="text-2xl font-light text-foreground mb-3">林间拾穗毕，愿君满载归。</h2>
        <p className="text-muted-foreground text-sm mb-8">今日之阅已尽，静待明日新启。</p>
        <Link href="/settings">
          <Button variant="ghost" className="text-muted-foreground hover:text-foreground">
            <Settings className="w-4 h-4 mr-2" />
            调整设定
          </Button>
        </Link>
      </div>
    )
  }

  if (isReading) {
    return (
      <div className="min-h-screen bg-card reading-enter">
        <div className="max-w-2xl mx-auto p-6 sm:p-8">
          <div className="flex items-center justify-end mb-6">
            <Button
              variant="ghost"
              onClick={() => setIsReading(false)}
              className="text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
          <article className="prose prose-lg max-w-none">
            {currentArticle && (
              <>
                <h1 className="text-3xl sm:text-4xl font-light text-foreground mb-3">{currentArticle.title}</h1>
                <div className="text-sm text-muted-foreground mb-6 flex items-center gap-3">
                  <span>{currentArticle.source_name}</span>
                  <span className="opacity-50">•</span>
                  <span>{currentArticle.published_at}</span>
                </div>
                <div className="text-foreground/80 leading-relaxed whitespace-pre-line text-base sm:text-lg">
                  {currentArticle.content}
                </div>
              </>
            )}
          </article>
          {currentArticle && (
            <div className="mt-10 pt-6 border-t border-border">
              <div className="flex justify-center gap-3 sm:gap-4">
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => {
                    handleAction("dislike")
                    setIsReading(false)
                  }}
                  disabled={isTransitioning || isRevealingNext}
                  className="bg-transparent text-muted-foreground hover:text-foreground hover:border-foreground/50 border-border active:scale-95"
                >
                  <X className="w-5 h-5 mr-2" />
                  不合意
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => {
                    handleAction("read")
                    setIsReading(false)
                  }}
                  disabled={isTransitioning || isRevealingNext}
                  className="bg-transparent text-muted-foreground hover:text-foreground hover:border-foreground/50 border-border active:scale-95"
                >
                  <BookOpen className="w-5 h-5 mr-2" />
                  下一篇
                </Button>
                <Button
                  variant="outline"
                  size="lg"
                  onClick={() => {
                    handleAction("like")
                    setIsReading(false)
                  }}
                  disabled={isTransitioning || isRevealingNext}
                  className="bg-transparent text-accent-foreground hover:text-accent-foreground/80 hover:border-accent border-accent/50 active:scale-95"
                >
                  <Heart className="w-5 h-5 mr-2" />
                  心喜之
                </Button>
              </div>
              <p className="text-center mt-6 text-xs text-muted-foreground">轻点以示，助我知您所好。</p>
            </div>
          )}
        </div>
      </div>
    )
  }

  const getCardClassName = () => {
    let classes = "w-full bg-card backdrop-blur-sm cursor-pointer card-current rounded-lg"
    if (isTransitioning && !isRevealingNext) {
      classes += " card-exit"
    } else if (isRevealingNext) {
      classes += " card-reveal"
    }
    return classes
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center pt-8 sm:pt-12 page-container">
      <header className="w-full max-w-2xl flex justify-between items-center mb-8 sm:mb-12">
        <h1 className="text-2xl sm:text-3xl font-light text-foreground">格物</h1>
        <Link href="/settings">
          <Button variant="ghost" size="icon" className="text-muted-foreground hover:text-foreground">
            <Settings className="w-5 h-5" />
          </Button>
        </Link>
      </header>

      <main className="w-full max-w-2xl flex-grow">
        <div className="relative card-stack h-[520px] sm:h-[550px]">
          {currentArticle && (
            <Card
              key={currentArticle.id}
              className={getCardClassName()}
              style={{ opacity: isRevealingNext ? undefined : isTransitioning ? undefined : 1 }}
              onClick={handleCardClick}
            >
              <CardContent className="p-6 sm:p-8 space-y-5 sm:space-y-6">
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground font-medium tracking-wider uppercase">
                    {currentArticle.source_name}
                  </p>
                  <h2 className="text-xl sm:text-2xl font-light text-foreground leading-snug sm:leading-tight">
                    {currentArticle.title}
                  </h2>
                </div>
                <div className="space-y-4">
                  <div className="bg-secondary/50 p-4 rounded-md border-l-2 border-accent">
                    <h3 className="text-xs text-accent-foreground font-medium mb-1.5">AI 推荐</h3>
                    <p className="text-sm text-foreground/70 leading-relaxed">{currentArticle.ai_rationale}</p>
                  </div>

                  <div>
                    <h3 className="text-xs text-muted-foreground font-medium mb-1.5">摘要</h3>
                    <p className="text-sm text-foreground/70 leading-relaxed line-clamp-3 sm:line-clamp-4">
                      {currentArticle.ai_summary}
                    </p>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-4 sm:pt-5 border-t border-border">
                  <p className="text-xs text-muted-foreground">{currentArticle.published_at}</p>
                  <p className="text-xs text-accent-foreground opacity-0 group-hover:opacity-100 transition-opacity">
                    轻触以阅全文
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </main>

      <footer className="w-full max-w-2xl py-8">
        <div className="flex justify-center gap-3 sm:gap-4 mb-6">
          <Button
            variant="outline"
            size="lg"
            onClick={() => handleAction("dislike")}
            disabled={isTransitioning || isRevealingNext}
            className="bg-card text-muted-foreground hover:text-foreground hover:border-foreground/30 border-border rounded-full px-6 active:scale-95"
          >
            <X className="w-5 h-5 mr-2" />
            不合意
          </Button>
          <Button
            variant="outline"
            size="lg"
            onClick={() => handleAction("read")}
            disabled={isTransitioning || isRevealingNext}
            className="bg-card text-muted-foreground hover:text-foreground hover:border-foreground/30 border-border rounded-full px-6 active:scale-95"
          >
            <BookOpen className="w-5 h-5 mr-2" />
            下一篇
          </Button>
        </div>
        <p className="text-center text-xs text-muted-foreground">
          {articles.length > 0 ? `尚余 ${articles.length - 1 < 0 ? 0 : articles.length - 1} 篇待阅` : "今日已尽"}
        </p>
      </footer>
    </div>
  )
}
