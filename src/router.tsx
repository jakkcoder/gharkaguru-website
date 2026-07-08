import { createBrowserRouter } from 'react-router-dom'
import App from './App'
import { routerBasename } from './lib/publicUrl'
import { HomePage } from './views/HomePage'
import { SearchPage } from './views/SearchPage'
import { ShortlistPage } from './views/ShortlistPage'
import { TutorProfilePage } from './views/TutorProfilePage'
import { NotFoundPage } from './views/NotFoundPage'
import { AuthPage } from './views/AuthPage'
import { StudentDashboardPage } from './views/student/StudentDashboardPage'
import { TeacherDashboardPage } from './views/teacher/TeacherDashboardPage'
import { TeacherRegisterPage } from './views/teacher/TeacherRegisterPage'
import { AboutPage } from './views/static/AboutPage'
import { ContactPage } from './views/static/ContactPage'
import { FaqPage } from './views/static/FaqPage'
import { PrivacyPage } from './views/static/PrivacyPage'
import { TermsPage } from './views/static/TermsPage'
import { GenericErrorPage } from './views/static/GenericErrorPage'

export const router = createBrowserRouter(
  [
    {
      path: '/',
      element: <App />,
      children: [
        { index: true, element: <HomePage /> },
        { path: 'search', element: <SearchPage /> },
        { path: 'tutor/:tutorId/:slug?', element: <TutorProfilePage /> },
        { path: 'shortlist', element: <ShortlistPage /> },
        { path: 'login', element: <AuthPage /> },
        { path: 'signup', element: <AuthPage /> },
        { path: 'student/dashboard', element: <StudentDashboardPage /> },
        { path: 'teacher/dashboard', element: <TeacherDashboardPage /> },
        { path: 'teacher/register', element: <TeacherRegisterPage /> },
        { path: 'about', element: <AboutPage /> },
        { path: 'contact', element: <ContactPage /> },
        { path: 'faq', element: <FaqPage /> },
        { path: 'privacy', element: <PrivacyPage /> },
        { path: 'terms', element: <TermsPage /> },
        { path: 'error', element: <GenericErrorPage /> },
        { path: '404', element: <NotFoundPage /> },
        { path: '*', element: <NotFoundPage /> },
      ],
    },
  ],
  { basename: routerBasename() || undefined },
)

