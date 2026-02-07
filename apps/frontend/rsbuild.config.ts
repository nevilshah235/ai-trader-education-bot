import { defineConfig } from '@rsbuild/core';
import { pluginReact } from '@rsbuild/plugin-react';
import { pluginSass } from '@rsbuild/plugin-sass';
import { pluginBasicSsl } from '@rsbuild/plugin-basic-ssl';

const path = require('path');

// In a monorepo, deps are hoisted to root; resolve from workspace root
const rootNodeModules = path.resolve(__dirname, '../../node_modules');

export default defineConfig({
    plugins: [
        pluginSass({
            sassLoaderOptions: {
                sourceMap: true,
                sassOptions: {
                    // includePaths: [path.resolve(__dirname, 'src')],
                },
                // additionalData: `@use "${path.resolve(__dirname, 'src/components/shared/styles')}" as *;`,
            },
            exclude: /node_modules/,
        }),
        pluginReact(),
        pluginBasicSsl(),
    ],
    source: {
        entry: {
            index: './src/main.tsx',
        },
        define: {
            'process.env': {
                TRANSLATIONS_CDN_URL: JSON.stringify(process.env.TRANSLATIONS_CDN_URL),
                R2_PROJECT_NAME: JSON.stringify(process.env.R2_PROJECT_NAME),
                CROWDIN_BRANCH_NAME: JSON.stringify(process.env.CROWDIN_BRANCH_NAME),
                TRACKJS_TOKEN: JSON.stringify(process.env.TRACKJS_TOKEN),
                APP_ENV: JSON.stringify(process.env.APP_ENV),
                REF_NAME: JSON.stringify(process.env.REF_NAME),
                REMOTE_CONFIG_URL: JSON.stringify(process.env.REMOTE_CONFIG_URL),
                GD_CLIENT_ID: JSON.stringify(process.env.GD_CLIENT_ID),
                GD_APP_ID: JSON.stringify(process.env.GD_APP_ID),
                GD_API_KEY: JSON.stringify(process.env.GD_API_KEY),
                DATADOG_SESSION_REPLAY_SAMPLE_RATE: JSON.stringify(process.env.DATADOG_SESSION_REPLAY_SAMPLE_RATE),
                DATADOG_SESSION_SAMPLE_RATE: JSON.stringify(process.env.DATADOG_SESSION_SAMPLE_RATE),
                DATADOG_APPLICATION_ID: JSON.stringify(process.env.DATADOG_APPLICATION_ID),
                DATADOG_CLIENT_TOKEN: JSON.stringify(process.env.DATADOG_CLIENT_TOKEN),
                RUDDERSTACK_KEY: JSON.stringify(process.env.RUDDERSTACK_KEY),
                GROWTHBOOK_CLIENT_KEY: JSON.stringify(process.env.GROWTHBOOK_CLIENT_KEY),
                GROWTHBOOK_DECRYPTION_KEY: JSON.stringify(process.env.GROWTHBOOK_DECRYPTION_KEY),
                POSTHOG_KEY: JSON.stringify(process.env.POSTHOG_KEY),
                POSTHOG_HOST: JSON.stringify(process.env.POSTHOG_HOST),
                CLIENT_ID: JSON.stringify(process.env.CLIENT_ID),
                EDUCATION_API_URL: JSON.stringify(process.env.EDUCATION_API_URL),
                // Use empty string to hit same-origin /api (proxied to backend); set AGENT_ANALYSIS_API_URL for direct backend URL
                AGENT_ANALYSIS_API_URL: JSON.stringify(process.env.AGENT_ANALYSIS_API_URL ?? ''),
                DERIV_APP_ID: JSON.stringify(process.env.DERIV_APP_ID),
                DERIV_OAUTH_REDIRECT_URI: JSON.stringify(process.env.DERIV_OAUTH_REDIRECT_URI),
            },
        },
        alias: {
            react: path.join(rootNodeModules, 'react'),
            'react-dom': path.join(rootNodeModules, 'react-dom'),
            '@/external': path.resolve(__dirname, './src/external'),
            '@/components': path.resolve(__dirname, './src/components'),
            '@/hooks': path.resolve(__dirname, './src/hooks'),
            '@/utils': path.resolve(__dirname, './src/utils'),
            '@/constants': path.resolve(__dirname, './src/constants'),
            '@/stores': path.resolve(__dirname, './src/stores'),
        },
    },
    output: {
        // Use 'auto' so chunks load from current origin (works when opened via ngrok after OAuth redirect)
        publicPath: 'auto',
        copy: [
            {
                from: path.join(rootNodeModules, '@deriv-com/smartcharts-champion/dist/*'),
                to: 'js/smartcharts/[name][ext]',
                globOptions: {
                    ignore: ['**/*.LICENSE.txt'],
                },
            },
            {
                from: path.join(rootNodeModules, '@deriv-com/smartcharts-champion/dist/assets/*'),
                to: 'assets/[name][ext]',
            },
            {
                from: path.join(rootNodeModules, '@deriv-com/smartcharts-champion/dist/assets/fonts/*'),
                to: 'assets/fonts/[name][ext]',
            },
            {
                from: path.join(rootNodeModules, '@deriv-com/smartcharts-champion/dist/assets/shaders/*'),
                to: 'assets/shaders/[name][ext]',
            },
            { from: path.join(__dirname, 'public') },
        ],
    },
    html: {
        template: './index.html',
    },
    server: {
        host: '0.0.0.0',
        port: 8443,
        compress: true,
        // Serve index.html for all routes so /redirect/ (Deriv OAuth callback) loads the SPA
        historyApiFallback: true,
        // Proxy /api to backend to avoid mixed content (HTTPS → HTTP) and CORS issues
        proxy: {
            '/api': 'http://localhost:8000',
        },
    },
    dev: {
        hmr: true,
    },
    performance: {
        // Configure Rsbuild's native bundle analyzer
        bundleAnalyze:
            process.env.BUNDLE_ANALYZE === 'true'
                ? {
                      analyzerMode: 'server',
                      analyzerHost: 'localhost',
                      analyzerPort: 8888,
                      openAnalyzer: true,
                      generateStatsFile: true,
                      statsFilename: 'stats.json',
                  }
                : undefined,
    },
    tools: {
        rspack: {
            plugins: [],
            resolve: {},
            module: {
                rules: [
                    {
                        test: /\.xml$/,
                        exclude: /node_modules/,
                        use: 'raw-loader',
                    },
                ],
            },
        },
    },
});
