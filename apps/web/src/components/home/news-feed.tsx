"use client";

import { useEffect, useState } from "react";
import { Newspaper } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface NewsItem {
  title: string;
  description: string;
  link: string;
  image: string | null;
  pub_date: string | null;
}

const API = process.env.NEXT_PUBLIC_API_URL || "";

export function NewsFeed() {
  const [articles, setArticles] = useState<NewsItem[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch(`${API}/api/v1/news?limit=8`)
      .then((r) => (r.ok ? r.json() : []))
      .then((data) => { setArticles(data); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Newspaper className="h-5 w-5" />
            Latest News
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="animate-pulse flex gap-3">
                <div className="w-20 h-14 bg-muted rounded shrink-0" />
                <div className="flex-1 space-y-2">
                  <div className="h-4 bg-muted rounded w-3/4" />
                  <div className="h-3 bg-muted rounded w-full" />
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (articles.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Newspaper className="h-5 w-5" />
            Latest News
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground text-center py-4">News unavailable</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Newspaper className="h-5 w-5" />
          Latest News
        </CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-0">
        {articles.map((article, idx) => (
          <a
            key={article.link}
            href={article.link}
            target="_blank"
            rel="noopener noreferrer"
            className={`flex gap-3 py-3 -mx-2 px-2 rounded-md transition-colors hover:bg-muted/50 ${
              idx < articles.length - 1 ? "border-b border-border/50" : ""
            }`}
          >
            {article.image && (
              <img
                src={article.image}
                alt=""
                className="w-20 h-14 object-cover rounded shrink-0"
              />
            )}
            <div className="flex-1 min-w-0">
              <p className="text-sm text-foreground line-clamp-2 leading-snug">
                {article.title}
              </p>
              <p className="text-xs text-muted-foreground mt-1 line-clamp-1">
                {article.description}
              </p>
              {article.pub_date && (
                <p className="text-[10px] text-muted-foreground mt-1">
                  {new Date(article.pub_date).toLocaleDateString("en-US", {
                    month: "short", day: "numeric", hour: "2-digit", minute: "2-digit",
                  })}
                </p>
              )}
            </div>
          </a>
        ))}
      </CardContent>
    </Card>
  );
}
