import React, { useState, useEffect } from 'react';
import { Search, Globe, Plus, X, AlertCircle, CheckCircle, Loader, TrendingUp, ExternalLink, Sparkles, Zap, ChevronDown, ChevronUp, Filter, BarChart3 } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';
import { Bar, Pie } from 'react-chartjs-2';
import './App.css';

ChartJS.register(CategoryScale, LinearScale, BarElement, ArcElement, Title, Tooltip, Legend);

const NewsScraperApp = () => {
  const [urls, setUrls] = useState(['https://www.bbc.com']);
  const [filters, setFilters] = useState(['technology']);
  const [categories, setCategories] = useState(['news']);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');
  const [selectedSentiment, setSelectedSentiment] = useState('all');
  const [selectedCategory, setSelectedCategory] = useState('all');

  // States for ML Analysis and Summarization
  const [summarizing, setSummarizing] = useState({});
  const [summaries, setSummaries] = useState({});
  const [expandedSummaries, setExpandedSummaries] = useState({});

  // States for Trending News
  const [trendingArticles, setTrendingArticles] = useState([]);
  const [loadingTrending, setLoadingTrending] = useState(false);

  // --- API FETCH LOGIC ---

  const fetchTrendingNews = async () => {
    setLoadingTrending(true);
    try {
      const response = await fetch("http://localhost:8000/trending");
      if (!response.ok) throw new Error("Failed to fetch trending news");
      const data = await response.json();

      // We must preprocess the data to add necessary ML fields (sentiment/category)
      // Since the Guardian API doesn't provide these, we'll initialize them for consistency.
      const processedArticles = data.articles.map(article => ({
          ...article,
          sentiment: article.sentiment || 'neutral', // Use placeholder or real data if scraping it
          category: article.category || 'General',
          relevance_score: article.relevance_score || 500, // Placeholder
      }));
      setTrendingArticles(processedArticles);
    } catch (err) {
      console.error("Error fetching trending news:", err);
    } finally {
      setLoadingTrending(false);
    }
  };

  useEffect(() => {
    fetchTrendingNews();
  }, []);

  const handleSummarize = async (articleUrl, stateKey) => {
    setSummarizing(prev => ({ ...prev, [stateKey]: true }));

    try {
      const response = await fetch("http://localhost:8000/summarize", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: articleUrl }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Summarization failed');
      }

      const data = await response.json();

      setSummaries(prev => ({
        ...prev,
        [stateKey]: data
      }));

      setExpandedSummaries(prev => ({
        ...prev,
        [stateKey]: true
      }));

    } catch (err) {
      setSummaries(prev => ({
        ...prev,
        [stateKey]: { error: err.message }
      }));
      setExpandedSummaries(prev => ({
        ...prev,
        [stateKey]: true
      }));
    } finally {
      setSummarizing(prev => ({ ...prev, [stateKey]: false }));
    }
  };

  const toggleSummary = (stateKey) => {
    setExpandedSummaries(prev => ({
      ...prev,
      [stateKey]: !prev[stateKey]
    }));
  };

  // --- END OF API FETCH LOGIC ---

  const addUrlField = () => setUrls([...urls, '']);
  const addFilterField = () => setFilters([...filters, '']);
  const addCategoryField = () => setCategories([...categories, '']);

  const updateUrl = (index, value) => {
    const newUrls = [...urls];
    newUrls[index] = value;
    setUrls(newUrls);
  };

  const updateFilter = (index, value) => {
    const newFilters = [...filters];
    newFilters[index] = value;
    setFilters(newFilters);
  };

  const updateCategory = (index, value) => {
    const newCategories = [...categories];
    newCategories[index] = value;
    setCategories(newCategories);
  };

  const removeUrl = (index) => {
    if (urls.length > 1) {
      setUrls(urls.filter((_, i) => i !== index));
    }
  };

  const removeFilter = (index) => {
    if (filters.length > 1) {
      setFilters(filters.filter((_, i) => i !== index));
    }
  };

  const removeCategory = (index) => {
    if (categories.length > 1) {
      setCategories(categories.filter((_, i) => i !== index));
    }
  };

  const handleScrape = async () => {
    const validUrls = urls.filter(url => url.trim());
    const validFilters = filters.filter(f => f.trim());
    const validCategories = categories.filter(c => c.trim());

    if (validUrls.length === 0 || validFilters.length === 0) {
      setError('Please add at least one URL and one filter');
      return;
    }

    setLoading(true);
    setError('');
    setArticles([]);
    setStats(null);
    setSummaries({});
    setExpandedSummaries({});

    try {
      const response = await fetch('http://localhost:8000/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: validUrls,
          filters: validFilters,
          categories: validCategories,
          max_results: 30,
          force_refresh: false
        })
      });

      if (!response.ok) {
        throw new Error('Scraping failed');
      }

      const data = await response.json();
      setArticles(data.articles);
      setStats({
        total: data.total,
        time: data.processing_time,
        sources: data.sources_scraped,
        errors: data.errors || []
      });
    } catch (err) {
      setError('Failed to scrape articles. Make sure the backend is running at http://localhost:8000');
    } finally {
      setLoading(false);
    }
  };


  // --- VISUALIZATION & FILTER DATA CALCULATION ---

  // Combine articles and trendingArticles for visualizations
  const allArticles = [...articles, ...trendingArticles];

  const uniqueSources = [...new Set(allArticles.map(a => a.source))];
  const uniqueSentiments = [...new Set(allArticles.map(a => a.sentiment).filter(s => s))];
  const uniqueCategories = [...new Set(allArticles.map(a => a.category).filter(c => c))];

  let filteredArticles = articles;
  if (selectedSource !== 'all') {
    filteredArticles = filteredArticles.filter(a => a.source === selectedSource);
  }
  if (selectedSentiment !== 'all') {
    filteredArticles = filteredArticles.filter(a => a.sentiment === selectedSentiment);
  }
  if (selectedCategory !== 'all') {
    filteredArticles = filteredArticles.filter(a => a.category === selectedCategory);
  }

  // Visualization data (using allArticles)
  const sourceData = {
    labels: uniqueSources,
    datasets: [{
      label: 'Articles per Source',
      data: uniqueSources.map(source => allArticles.filter(a => a.source === source).length),
      backgroundColor: 'rgba(30, 64, 175, 0.6)',
    }],
  };

  const sentimentCounts = {
    positive: allArticles.filter(a => a.sentiment === 'positive').length,
    negative: allArticles.filter(a => a.sentiment === 'negative').length,
    neutral: allArticles.filter(a => a.sentiment === 'neutral').length,
    general: allArticles.filter(a => !a.sentiment || a.sentiment === 'General').length,
  };

  const sentimentLabels = ['Positive', 'Negative', 'Neutral'];
  const sentimentBackgrounds = ['#10b981', '#ef4444', '#f59e0b'];
  if (sentimentCounts.general > 0) {
      sentimentLabels.push('Unanalyzed');
      sentimentBackgrounds.push('#9ca3af');
  }

  const sentimentData = {
    labels: sentimentLabels,
    datasets: [{
      data: [sentimentCounts.positive, sentimentCounts.negative, sentimentCounts.neutral, sentimentCounts.general].filter(count => count > 0),
      backgroundColor: sentimentBackgrounds.filter((_, index) => [sentimentCounts.positive, sentimentCounts.negative, sentimentCounts.neutral, sentimentCounts.general][index] > 0),
    }],
  };

  // --- JSX RENDER ---

  const renderSummarySection = (stateKey) => (
      summaries[stateKey] && (
        <div className="summary-section">
          <button
            onClick={() => toggleSummary(stateKey)}
            className="summary-toggle"
          >
            <span className="summary-toggle-label">
              <Sparkles className="icon-small" />
              AI Generated Summary
            </span>
            {expandedSummaries[stateKey] ? (
              <ChevronUp className="icon-small" />
            ) : (
              <ChevronDown className="icon-small" />
            )}
          </button>

          {expandedSummaries[stateKey] && (
            <div className="summary-content">
              {summaries[stateKey].error ? (
                <div className="summary-error">
                  <p className="summary-error-title">⚠️ Error:</p>
                  <p>{summaries[stateKey].error}</p>
                  <p className="summary-error-tip">
                    Tip: Make sure the article URL is accessible and contains readable content.
                  </p>
                </div>
              ) : (
                <div>
                  <p className="summary-text">
                    {summaries[stateKey].summary}
                  </p>
                  <div className="summary-stats">
                    <span className="summary-stat">
                      📄 Original: {summaries[stateKey].original_length} chars
                    </span>
                    <span className="summary-stat">
                      ✨ Summary: {summaries[stateKey].summary_length} chars
                    </span>
                    <span className="summary-stat">
                      🎯 Compression: {summaries[stateKey].compression_ratio}%
                    </span>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )
  );

  const renderArticleCard = (article, index, prefix) => {
    const stateKey = `${prefix}-${index}`;
    return (
        <article key={stateKey} className="article-card">
          <div className="article-content">

            {/* Article Header */}
            <div className="article-header">
              <div className="article-source-badge">
                {article.source}
              </div>
              {article.relevance_score && article.relevance_score > 0 && (
                <div className="article-score-badge">
                  {article.relevance_score >= 1000
                    ? `${(article.relevance_score / 1000).toFixed(1)}k`
                    : article.relevance_score}★
                </div>
              )}
              {article.sentiment && (
                <div className={`article-sentiment-badge ${article.sentiment}`}>
                  {article.sentiment.charAt(0).toUpperCase() + article.sentiment.slice(1)}
                </div>
              )}
              {article.category && (
                <div className="article-category-badge">
                  {article.category}
                </div>
              )}
            </div>

            {/* Thumbnail for Trending News */}
            {prefix === 'T' && article.thumbnail && (
              <img src={article.thumbnail} alt="thumbnail" style={{ width: '100%', borderRadius: '6px', marginBottom: '10px' }} />
            )}

            {/* Article Title */}
            <a
              href={article.url}
              target="_blank"
              rel="noopener noreferrer"
              className="article-link"
            >
              <h3 className="article-title">
                {article.headline}
                <ExternalLink className="article-external-icon" />
              </h3>
            </a>

            {/* Article Description */}
            {article.description && (
              <p className="article-description" dangerouslySetInnerHTML={{ __html: article.description }} />
            )}

            {/* Action Buttons */}
            <div className="article-actions">
              <a
                href={article.url}
                target="_blank"
                rel="noopener noreferrer"
                className="action-button primary"
              >
                <ExternalLink className="icon-small" />
                Read Article
              </a>

              <button
                onClick={() => handleSummarize(article.url, stateKey)}
                disabled={summarizing[stateKey]}
                className="action-button secondary"
              >
                {summarizing[stateKey] ? (
                  <>
                    <Loader className="icon-small animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Sparkles className="icon-small" />
                    AI Summary
                  </>
                )}
              </button>
            </div>

            {/* Summary Display */}
            {renderSummarySection(stateKey)}
          </div>
        </article>
  );
  };

  return (
    <div className="app-container">
      <div className="main-wrapper">

        {/* Professional Header */}
        <header className="app-header">
          <div className="header-background"></div>
          <div className="header-content">
            <div className="brand-section">
              <div className="brand-icon">
                <Zap className="icon-large" />
              </div>
              <div className="brand-info">
                <h1 className="brand-title">NewsFlux AI</h1>
                <p className="brand-subtitle">
                  Intelligent News Aggregation • Real-time Scraping • AI-Powered Insights
                </p>
              </div>
            </div>
            <div className="feature-badges">
              <div className="badge">
                <span>⚡ Lightning Fast</span>
              </div>
              <div className="badge">
                <span>🤖 AI Summarization</span>
              </div>
              <div className="badge">
                <span>🌐 Multi-Source</span>
              </div>
            </div>
          </div>
        </header>

        {/* Input Section */}
        <div className="input-section">
          <div className="input-grid">

            {/* URLs */}
            <div className="input-column">
              <h3 className="section-title">
                <Globe className="icon-small" />
                News Websites
              </h3>
              {urls.map((url, index) => (
                <div key={index} className="input-row">
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => updateUrl(index, e.target.value)}
                    placeholder="https://www.bbc.com"
                    className="text-input"
                  />
                  {urls.length > 1 && (
                    <button
                      onClick={() => removeUrl(index)}
                      className="remove-button"
                      aria-label="Remove URL"
                    >
                      <X className="icon-small" />
                    </button>
                  )}
                </div>
              ))}
              <button onClick={addUrlField} className="add-button">
                <Plus className="icon-small" /> Add Website
              </button>
            </div>

            {/* Filters */}
            <div className="input-column">
              <h3 className="section-title">
                <Search className="icon-small" />
                Search Topics
              </h3>
              {filters.map((filter, index) => (
                <div key={index} className="input-row">
                  <input
                    type="text"
                    value={filter}
                    onChange={(e) => updateFilter(index, e.target.value)}
                    placeholder="technology, sports, politics..."
                    className="text-input"
                  />
                  {filters.length > 1 && (
                    <button
                      onClick={() => removeFilter(index)}
                      className="remove-button"
                      aria-label="Remove filter"
                    >
                      <X className="icon-small" />
                    </button>
                  )}
                </div>
              ))}
              <button onClick={addFilterField} className="add-button">
                <Plus className="icon-small" /> Add Topic
              </button>
            </div>

            {/* Categories */}
            <div className="input-column">
              <h3 className="section-title">
                <Filter className="icon-small" />
                Categories (For ML)
              </h3>
              {categories.map((category, index) => (
                <div key={index} className="input-row">
                  <input
                    type="text"
                    value={category}
                    onChange={(e) => updateCategory(index, e.target.value)}
                    placeholder="news, business, entertainment..."
                    className="text-input"
                  />
                  {categories.length > 1 && (
                    <button
                      onClick={() => removeCategory(index)}
                      className="remove-button"
                      aria-label="Remove category"
                    >
                      <X className="icon-small" />
                    </button>
                  )}
                </div>
              ))}
              <button onClick={addCategoryField} className="add-button">
                <Plus className="icon-small" /> Add Category
              </button>
            </div>

          </div>

          <button
            onClick={handleScrape}
            disabled={loading}
            className="scrape-button"
          >
            {loading ? (
              <>
                <Loader className="icon-medium animate-spin" />
                Scraping Articles...
              </>
            ) : (
              <>
                <TrendingUp className="icon-medium" />
                Scrape News Articles
              </>
            )}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="error-message">
            <AlertCircle className="icon-medium" />
            <div className="error-text">{error}</div>
          </div>
        )}

        {/* Stats */}
        {stats && (
          <div className="stats-section">
            <CheckCircle className="icon-medium stats-icon" />
            <div className="stats-content">
              <div className="stats-main">
                Found <span className="stats-number">{stats.total}</span> articles in{' '}
                <span className="stats-number">{stats.time}s</span>
              </div>
              <div className="stats-sub">
                Scraped {stats.sources} sources successfully
              </div>
              {stats.errors && stats.errors.length > 0 && (
                <div className="stats-warning">
                  {stats.errors.length} source(s) had errors
                </div>
              )}
            </div>
          </div>
        )}

        {/* Visualizations */}
        {allArticles.length > 0 && (
          <div className="visualization-section">
            <h3 className="section-title">
              <BarChart3 className="icon-small" />
              Data Visualizations (Total Articles)
            </h3>
            <div className="charts-grid">
              <div className="chart-container">
                <h4>Articles per Source</h4>
                <Bar data={sourceData} options={{ responsive: true }} />
              </div>
              <div className="chart-container">
                <h4>Sentiment Distribution</h4>
                <Pie data={sentimentData} options={{ responsive: true }} />
              </div>
            </div>
          </div>
        )}

        {/* --- GUARDIAN TRENDING NEWS SECTION (with Summary/ML logic) --- */}
        <div style={{ marginTop: '40px', padding: '20px', backgroundColor: '#f9fafb', borderRadius: '12px' }}>
            <h3 style={{ fontSize: '1.5rem', marginBottom: '10px', display: 'flex', alignItems: 'center' }}>
                <TrendingUp style={{ marginRight: '8px' }} />
                **Trending News from The Guardian**
            </h3>
            <button
                onClick={fetchTrendingNews}
                disabled={loadingTrending}
                style={{
                    padding: '10px 16px',
                    backgroundColor: '#1d4ed8',
                    color: '#fff',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    marginBottom: '20px',
                    fontWeight: 'bold'
                }}
            >
                {loadingTrending ? 'Loading Trending News...' : 'Refresh Trending News'}
            </button>

            {trendingArticles.length > 0 && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '20px' }}>
                    {trendingArticles.map((article, index) => (
                        // Render using the reusable card component with prefix 'T'
                        renderArticleCard(article, index, 'T')
                    ))}
                </div>
            )}
        </div>
        {/* --- END OF GUARDIAN TRENDING NEWS SECTION --- */}


        {/* Filters (Applicable mostly to the Manual Scrape results + Trending) */}
        {allArticles.length > 0 && (
          <>
            {/* Source Filter */}
            <div className="filter-section">
              <div className="filter-label">
                <Filter className="icon-small" />
                <span>Filter by Source:</span>
              </div>
              <div className="filter-buttons">
                <button
                  onClick={() => setSelectedSource('all')}
                  className={`filter-button ${selectedSource === 'all' ? 'active' : ''}`}
                >
                  All ({articles.length})
                </button>
                {uniqueSources.map(source => (
                  <button
                    key={source}
                    onClick={() => setSelectedSource(source)}
                    className={`filter-button ${selectedSource === source ? 'active' : ''}`}
                  >
                    {source} ({allArticles.filter(a => a.source === source).length})
                  </button>
                ))}
              </div>
            </div>

            {/* Sentiment Filter */}
            <div className="filter-section">
              <div className="filter-label">
                <Filter className="icon-small" />
                <span>Filter by Sentiment:</span>
              </div>
              <div className="filter-buttons">
                <button
                  onClick={() => setSelectedSentiment('all')}
                  className={`filter-button ${selectedSentiment === 'all' ? 'active' : ''}`}
                >
                  All
                </button>
                {['positive', 'negative', 'neutral', 'General'].map(sentiment => (
                  <button
                    key={sentiment}
                    onClick={() => setSelectedSentiment(sentiment)}
                    className={`filter-button ${selectedSentiment === sentiment ? 'active' : ''}`}
                  >
                    {sentiment.charAt(0).toUpperCase() + sentiment.slice(1)} ({allArticles.filter(a => a.sentiment === sentiment).length})
                  </button>
                ))}
              </div>
            </div>

            {/* Category Filter */}
            <div className="filter-section">
              <div className="filter-label">
                <Filter className="icon-small" />
                <span>Filter by Category:</span>
              </div>
              <div className="filter-buttons">
                <button
                  onClick={() => setSelectedCategory('all')}
                  className={`filter-button ${selectedCategory === 'all' ? 'active' : ''}`}
                >
                  All
                </button>
                {uniqueCategories.map(category => (
                  <button
                    key={category}
                    onClick={() => setSelectedCategory(category)}
                    className={`filter-button ${selectedCategory === category ? 'active' : ''}`}
                  >
                    {category} ({allArticles.filter(a => a.category === category).length})
                  </button>
                ))}
              </div>
            </div>
          </>
        )}

        {/* Articles Grid (Manual Scrape Results) */}
        <div className="articles-grid">
          {filteredArticles.map((article, index) => (
            // Render using the reusable card component with prefix 'A'
            renderArticleCard(article, index, 'A')
          ))}
        </div>

        {/* Empty State */}
        {!loading && articles.length === 0 && !error && trendingArticles.length === 0 && (
          <div className="empty-state">
            <div className="empty-state-icon">
              <Globe className="icon-xlarge" />
            </div>
            <p className="empty-state-title">Ready to Explore News</p>
            <p className="empty-state-subtitle">Add your sources and topics, then start scraping!</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default NewsScraperApp;
