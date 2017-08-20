const ExtractTextPlugin = require('extract-text-webpack-plugin')
const path = require('path')
const { env } = require('process')

const isProduction = env.NODE_ENV === 'production'

const loaders = {
  css: {
    loader: 'css-loader',
    options: { minimize: isProduction }
  },
  postcss: {
    loader: 'postcss-loader',
  },
  sass: {
    loader: 'sass-loader',
    // options: {
    //   includePaths: [path.resolve(__dirname, './src')]
    // }
  }
}

const config = {
  entry: {
    app: ['./cineapp/static/styles']
  },

  module: {
    rules: [
      {
        test: /\.(sass|scss|css)$/,
        use: ExtractTextPlugin.extract({
          fallback: 'style-loader',
          use: [loaders.css, loaders.postcss, loaders.sass]
        })
      },
    ]
  },

  output: {
    filename: '[name].js',
    path: path.join(__dirname, './build'),
    publicPath: '/build'
  },

  plugins: [new ExtractTextPlugin('[name].css')],

  resolve: {
    extensions: ['.scss', '.css', '.js'],
    modules: [path.join(__dirname, './src'), 'node_modules']
  }
}

module.exports = config
