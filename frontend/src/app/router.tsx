import { createBrowserRouter, Navigate } from 'react-router-dom'
import { Layout } from '@/shared/ui/Layout'
import { ProjectList } from '@/features/projects/ProjectList'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/projects" replace /> },
      { path: 'projects', element: <ProjectList /> },
    ],
  },
])
