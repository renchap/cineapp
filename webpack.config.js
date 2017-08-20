const ExtractTextPlugin = require('extract-text-webpack-plugin')
const webpack = require('webpack')
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

var styleLoader = [];

if(isProduction) {
  styleLoader = ExtractTextPlugin.extract({
    fallback: 'style-loader',
    use: [loaders.css, loaders.postcss, loaders.sass]
  })
} else {
  styleLoader = ['style-loader', loaders.css, loaders.postcss, loaders.sass]
}

const config = {
  entry: {
    app: ['./cineapp/static/index.js']
  },

  devServer: {
    contentBase: './',
    hot: !isProduction
  },

  module: {
    rules: [
      {
        test: /\.(sass|scss|css)$/,
        use: styleLoader
      },
      {
        test: /\.(jpg|jpeg|png|gif|svg|eot|ttf|woff|woff2)$/i,
        use: [{
          loader: 'file-loader',
          options: {
            name: '[name]-[hash].[ext]'
          }
        }]
      }
    ]
  },

  output: {
    filename: '[name].js',
    path: path.join(__dirname, 'build'),
    publicPath: '/build/'
  },

  plugins: !isProduction ? [new webpack.HotModuleReplacementPlugin()] : [new ExtractTextPlugin('[name].css')],

  resolve: {
    extensions: ['.scss', '.css', '.js'],
    modules: [path.join(__dirname, './src'), 'node_modules']
  }
}

module.exports = config
