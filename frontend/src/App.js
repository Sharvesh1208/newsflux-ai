import React, { useState } from 'react';
import { Search, Globe, Plus, X, AlertCircle, CheckCircle, Loader, TrendingUp } from 'lucide-react';
import './App.css';


const NewsScraperApp = () => {
  const [urls, setUrls] = useState(['https://www.bbc.com']);
  const [filters, setFilters] = useState(['technology']);
  const [articles, setArticles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState(null);
  const [error, setError] = useState('');
  const [selectedSource, setSelectedSource] = useState('all');

  const addUrlField = () => setUrls([...urls, '']);
  const addFilterField = () => setFilters([...filters, '']);

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

  const handleScrape = async () => {
    const validUrls = urls.filter(url => url.trim());
    const validFilters = filters.filter(f => f.trim());

    if (validUrls.length === 0 || validFilters.length === 0) {
      setError('Please add at least one URL and one filter');
      return;
    }

    setLoading(true);
    setError('');
    setArticles([]);
    setStats(null);

    try {
      const response = await fetch('http://localhost:8000/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          urls: validUrls,
          filters: validFilters,
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

  const uniqueSources = [...new Set(articles.map(a => a.source))];
  const filteredArticles = selectedSource === 'all' 
    ? articles 
    : articles.filter(a => a.source === selectedSource);

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-purple-50 to-pink-50">
      <div className="max-w-7xl mx-auto p-6">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-purple-600 rounded-2xl shadow-2xl p-8 mb-8 text-white">
          <div className="flex items-center gap-4 mb-4">
            <Globe className="w-12 h-12" />
            <div>
              <h1 className="text-4xl font-bold">Universal News Scraper</h1>
              <p className="text-blue-100 mt-2">Intelligent web scraping with automated profile detection</p>
            </div>
          </div>
        </div>

        {/* Input Section */}
        <div className="bg-white rounded-2xl shadow-xl p-8 mb-8">
          <div className="grid md:grid-cols-2 gap-8">
            {/* URLs */}
            <div>
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <Globe className="w-5 h-5 text-blue-600" />
                News Websites
              </h3>
              {urls.map((url, index) => (
                <div key={index} className="flex gap-2 mb-3">
                  <input
                    type="text"
                    value={url}
                    onChange={(e) => updateUrl(index, e.target.value)}
                    placeholder="https://www.bbc.com"
                    className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-blue-500 focus:outline-none transition-colors"
                  />
                  {urls.length > 1 && (
                    <button
                      onClick={() => removeUrl(index)}
                      className="p-3 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  )}
                </div>
              ))}
              <button
                onClick={addUrlField}
                className="w-full py-3 bg-blue-50 text-blue-600 rounded-lg hover:bg-blue-100 transition-colors flex items-center justify-center gap-2 font-medium"
              >
                <Plus className="w-5 h-5" /> Add Website
              </button>
            </div>

            {/* Filters */}
            <div>
              <h3 className="text-xl font-bold text-gray-800 mb-4 flex items-center gap-2">
                <Search className="w-5 h-5 text-purple-600" />
                Search Topics
              </h3>
              {filters.map((filter, index) => (
                <div key={index} className="flex gap-2 mb-3">
                  <input
                    type="text"
                    value={filter}
                    onChange={(e) => updateFilter(index, e.target.value)}
                    placeholder="technology, sports, politics..."
                    className="flex-1 px-4 py-3 border-2 border-gray-200 rounded-lg focus:border-purple-500 focus:outline-none transition-colors"
                  />
                  {filters.length > 1 && (
                    <button
                      onClick={() => removeFilter(index)}
                      className="p-3 bg-red-50 text-red-600 rounded-lg hover:bg-red-100 transition-colors"
                    >
                      <X className="w-5 h-5" />
                    </button>
                  )}
                </div>
              ))}
              <button
                onClick={addFilterField}
                className="w-full py-3 bg-purple-50 text-purple-600 rounded-lg hover:bg-purple-100 transition-colors flex items-center justify-center gap-2 font-medium"
              >
                <Plus className="w-5 h-5" /> Add Topic
              </button>
            </div>
          </div>

          <button
            onClick={handleScrape}
            disabled={loading}
            className="w-full mt-6 py-4 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-xl font-bold text-lg hover:from-blue-700 hover:to-purple-700 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-3"
          >
            {loading ? (
              <>
                <Loader className="w-6 h-6 animate-spin" />
                Scraping Articles...
              </>
            ) : (
              <>
                <TrendingUp className="w-6 h-6" />
                Scrape News Articles
              </>
            )}
          </button>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border-2 border-red-200 rounded-xl p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="text-red-800">{error}</div>
          </div>
        )}

        {/* Stats */}
        {stats && (
          <div className="bg-gradient-to-r from-green-50 to-emerald-50 border-2 border-green-200 rounded-xl p-6 mb-6">
            <div className="flex items-start gap-3 mb-3">
              <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0 mt-0.5" />
              <div>
                <div className="text-lg font-semibold text-green-900">
                  Found <span className="text-2xl">{stats.total}</span> articles in{' '}
                  <span className="text-2xl">{stats.time}s</span>
                </div>
                <div className="text-sm text-green-700 mt-1">
                  Scraped {stats.sources} sources successfully
                </div>
                {stats.errors && stats.errors.length > 0 && (
                  <div className="mt-2 text-sm text-orange-700">
                    {stats.errors.length} source(s) had errors
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Source Filter */}
        {articles.length > 0 && (
          <div className="mb-6 flex flex-wrap gap-2">
            <button
              onClick={() => setSelectedSource('all')}
              className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                selectedSource === 'all'
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              All ({articles.length})
            </button>
            {uniqueSources.map(source => (
              <button
                key={source}
                onClick={() => setSelectedSource(source)}
                className={`px-4 py-2 rounded-lg font-medium transition-colors ${
                  selectedSource === source
                    ? 'bg-blue-600 text-white'
                    : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                }`}
              >
                {source} ({articles.filter(a => a.source === source).length})
              </button>
            ))}
          </div>
        )}

        {/* Articles Grid */}
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredArticles.map((article, index) => (
            <div
              key={index}
              className="bg-white rounded-xl shadow-lg hover:shadow-2xl transition-all duration-300 overflow-hidden group cursor-pointer transform hover:-translate-y-1"
            >
              <div className="p-6">
                <div className="flex items-center gap-2 mb-3">
                  <div className="px-3 py-1 bg-blue-100 text-blue-700 rounded-full text-xs font-bold uppercase tracking-wide">
                    {article.source}
                  </div>
                  {article.relevance_score > 0 && (
                    <div className="px-2 py-1 bg-green-100 text-green-700 rounded-full text-xs font-bold">
                      {article.relevance_score}★
                    </div>
                  )}
                </div>
                
                <h3 className="text-lg font-bold text-gray-900 mb-3 line-clamp-3 group-hover:text-blue-600 transition-colors">
                  {article.headline}
                </h3>
                
                {article.description && (
                  <p className="text-gray-600 text-sm mb-4 line-clamp-3">
                    {article.description}
                  </p>
                )}
                
                <a
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-blue-600 font-medium hover:text-blue-700 transition-colors"
                >
                  Read Article
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </a>
              </div>
            </div>
          ))}
        </div>

        {/* Empty State */}
        {!loading && articles.length === 0 && !error && (
          <div className="text-center py-16">
            <Globe className="w-20 h-20 text-gray-300 mx-auto mb-4" />
            <p className="text-xl text-gray-500">No articles yet. Start scraping to see results!</p>
          </div>
        )}
      </div>
    </div>
  );
};

export default NewsScraperApp;