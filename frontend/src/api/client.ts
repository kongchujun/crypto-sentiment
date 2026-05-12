import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  timeout: 15000,
})

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const message =
      error?.response?.data?.detail ??
      error?.message ??
      'Request failed. Please try again.'
    return Promise.reject(new Error(typeof message === 'string' ? message : 'Request failed'))
  },
)
