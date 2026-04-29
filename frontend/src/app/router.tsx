import { createBrowserRouter, Navigate } from 'react-router-dom'
import { Layout } from '@/shared/ui/Layout'
import { ProjectList } from '@/features/projects/ProjectList'
import { Placeholder } from '@/shared/ui/Placeholder'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/projects" replace /> },
      { path: 'projects', element: <ProjectList /> },
      { path: 'dashboard', element: <Placeholder title="Dashboard" phase={5} /> },
      { path: '*', element: <Navigate to="/projects" replace /> },
    ],
  },
])
