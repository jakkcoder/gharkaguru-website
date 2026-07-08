import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Instagram, Linkedin, LogOut, User, Youtube } from 'lucide-react'
import * as DropdownMenu from '@radix-ui/react-dropdown-menu'
import { ScrollToTopButton } from './ScrollToTopButton'
import { useAuth } from '../../features/auth/useAuth'
import { publicUrl } from '../../lib/publicUrl'

export function AppShell({ children }: { children: ReactNode }) {
  const auth = useAuth()

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-40 border-b border-tn-border bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-16 max-w-[1200px] items-center justify-between px-4">
          <Link to="/" className="flex items-center gap-2 font-semibold text-tn-text">
            <img
              src={publicUrl('/assets/gharkaguru-logo.png')}
              alt="GharKaGuru logo"
              className="h-8 w-8 object-contain"
              loading="eager"
              decoding="async"
            />
            <span className="text-lg">GharKaGuru</span>
          </Link>
          <nav className="hidden items-center gap-4 text-sm md:flex">
            <Link to="/">Home</Link>
            <Link to="/search">For Students</Link>
            <Link to="/teacher/register">For Teachers</Link>
            <Link to="/about">About</Link>
            <Link to="/contact">Contact</Link>
          </nav>
          <div className="flex items-center gap-2 text-sm">
            <Link
              to="/shortlist"
              className="rounded-md px-3 py-2 text-tn-text hover:bg-tn-bg"
              aria-label="Shortlist"
            >
              Shortlist
            </Link>
            {auth.token ? (
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <button
                    className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-tn-bg text-tn-text hover:bg-tn-border/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-tn-primary focus-visible:ring-offset-2"
                    aria-label="User menu"
                  >
                    <User className="h-5 w-5" aria-hidden="true" />
                  </button>
                </DropdownMenu.Trigger>
                <DropdownMenu.Portal>
                  <DropdownMenu.Content
                    align="end"
                    className="z-50 w-56 rounded-xl border border-tn-border bg-white p-2 shadow-soft"
                  >
                    {auth.role === 'student' ? (
                      <>
                        <DropdownMenu.Item asChild>
                          <Link
                            to="/student/dashboard"
                            className="block rounded-md px-3 py-2 text-sm text-tn-text hover:bg-tn-bg focus:outline-none"
                          >
                            My Enquiries
                          </Link>
                        </DropdownMenu.Item>
                        <DropdownMenu.Item asChild>
                          <Link
                            to="/shortlist"
                            className="block rounded-md px-3 py-2 text-sm text-tn-text hover:bg-tn-bg focus:outline-none"
                          >
                            Shortlist
                          </Link>
                        </DropdownMenu.Item>
                      </>
                    ) : (
                      <>
                        <DropdownMenu.Item
                          className="cursor-not-allowed rounded-md px-3 py-2 text-sm text-tn-muted"
                          aria-disabled="true"
                        >
                          Manage Profile (coming soon)
                        </DropdownMenu.Item>
                        <DropdownMenu.Item asChild>
                          <Link
                            to="/teacher/dashboard"
                            className="block rounded-md px-3 py-2 text-sm text-tn-text hover:bg-tn-bg focus:outline-none"
                          >
                            Teacher Dashboard
                          </Link>
                        </DropdownMenu.Item>
                      </>
                    )}
                    <DropdownMenu.Separator className="my-2 h-px bg-tn-border" />
                    <DropdownMenu.Item
                      className="flex cursor-pointer items-center gap-2 rounded-md px-3 py-2 text-sm text-tn-text hover:bg-tn-bg focus:outline-none"
                      onSelect={() => auth.logout()}
                    >
                      <LogOut className="h-4 w-4" aria-hidden="true" />
                      Logout
                    </DropdownMenu.Item>
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
            ) : (
              <>
                <Link
                  to="/login"
                  className="rounded-md px-3 py-2 text-tn-text hover:bg-tn-bg"
                  aria-label="Login"
                >
                  Login
                </Link>
                <Link
                  to="/signup"
                  className="rounded-md bg-tn-primary px-3 py-2 font-medium text-white hover:bg-tn-primaryDark"
                  aria-label="Signup"
                >
                  Signup
                </Link>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto w-full max-w-[1200px] px-4 py-8">{children}</main>

      <footer className="border-t border-tn-border bg-white">
        <div className="mx-auto max-w-[1200px] px-4 py-8 text-sm text-tn-muted">
          <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
            <div className="flex flex-wrap gap-x-4 gap-y-2">
              <Link to="/privacy">Privacy</Link>
              <Link to="/terms">Terms</Link>
              <Link to="/faq">FAQs</Link>
              <Link to="/about">About</Link>
              <Link to="/contact">Contact</Link>
            </div>
            <div className="flex items-center gap-4">
              <div className="flex items-center gap-3">
                <a
                  href="#"
                  className="rounded-md p-2 hover:bg-tn-bg"
                  aria-label="GharKaGuru on YouTube"
                >
                  <Youtube className="h-5 w-5" aria-hidden="true" />
                </a>
                <a
                  href="#"
                  className="rounded-md p-2 hover:bg-tn-bg"
                  aria-label="GharKaGuru on LinkedIn"
                >
                  <Linkedin className="h-5 w-5" aria-hidden="true" />
                </a>
                <a
                  href="#"
                  className="rounded-md p-2 hover:bg-tn-bg"
                  aria-label="GharKaGuru on Instagram"
                >
                  <Instagram className="h-5 w-5" aria-hidden="true" />
                </a>
              </div>
              <div>© 2026 GharKaGuru</div>
            </div>
          </div>
        </div>
      </footer>

      <ScrollToTopButton />
    </div>
  )
}

