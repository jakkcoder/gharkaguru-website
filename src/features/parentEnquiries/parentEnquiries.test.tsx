import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { parentPhoneForDisplay, type ParentEnquiry } from '../../api/parentEnquiries'
import { EnquiryCard } from './EnquiryCard'
import { PolicyAcknowledgements } from './PolicyAcknowledgements'

const enquiry: ParentEnquiry = {
  id: 'lead-1',
  status: 'open',
  parentName: 'S',
  studentName: 'Kartavya',
  classLevel: '10',
  subject: 'Maths, Science',
  board: 'CBSE',
  medium: 'English',
  tutorMode: 'Home tutor',
  teacherPreference: 'Male',
  address: 'Raja Puri, Delhi',
  pin: '110059',
  budget: '5000',
  notes: 'Need home tutor',
  schedule: '',
  updatedAt: '2026-09-30T00:00:00Z',
}

describe('parent enquiries', () => {
  it('shows the enquiry without a parent phone number', () => {
    render(
      <MemoryRouter>
        <EnquiryCard enquiry={enquiry} />
      </MemoryRouter>,
    )
    expect(screen.getByRole('link', { name: /move forward/i })).toHaveAttribute('href', '/parent-enquiries/lead-1')
    expect(screen.getByText(/Kartavya/)).toBeInTheDocument()
    expect(screen.getByText(/Class 10/)).toBeInTheDocument()
    expect(screen.queryByText(/Class Class/)).not.toBeInTheDocument()
    expect(screen.getByText(/Maths, Science/)).toBeInTheDocument()
    expect(screen.getByText(/Raja Puri, Delhi/)).toBeInTheDocument()
    expect(screen.queryByText(/parent phone/i)).not.toBeInTheDocument()
    expect(screen.queryByText(/\+91/)).not.toBeInTheDocument()
  })

  it('links each enquiry to the demo app without parent details', () => {
    const { container } = render(
      <MemoryRouter>
        <EnquiryCard enquiry={enquiry} teacherPhone="9876543210" />
      </MemoryRouter>,
    )
    const href = within(container).getByRole('link', { name: /submit your demo/i }).getAttribute('href') || ''
    expect(href.startsWith('/demo/?')).toBe(true)
    const params = new URLSearchParams(href.split('?')[1])
    expect(params.get('lead_id')).toBe('lead-1')
    expect(params.get('subject')).toBe('Maths, Science')
    expect(params.get('class_level')).toBe('10')
    expect(params.get('area')).toBe('Raja Puri, Delhi')
    expect(params.get('phone')).toBe('9876543210')
    expect(params.get('teacher_preference')).toBe('Male')
    expect(params.has('schedule')).toBe(false)
    expect(href).not.toMatch(/parent/i)
  })

  it('demo link leaves the phone out when no teacher is logged in', () => {
    const { container } = render(
      <MemoryRouter>
        <EnquiryCard enquiry={enquiry} />
      </MemoryRouter>,
    )
    const href = within(container).getByRole('link', { name: /submit your demo/i }).getAttribute('href') || ''
    expect(new URLSearchParams(href.split('?')[1]).has('phone')).toBe(false)
  })

  it('reveals a parent phone only after payment', () => {
    expect(parentPhoneForDisplay('pending', '9876543210')).toBe('')
    expect(parentPhoneForDisplay('paid', '9876543210')).toBe('9876543210')
  })

  it('requires every acknowledgement before continuing', async () => {
    const user = userEvent.setup()
    const onAccept = vi.fn()
    render(
      <PolicyAcknowledgements
        policy={{
          version: '2026-10-01',
          text: 'No refund if the demo fails. 25% of the first tuition payment is owed.',
          hash: 'abc',
          firstFeeRupees: 100,
          nextFeeRupees: 500,
          commissionPercent: 25,
        }}
        feeRupees={100}
        submitting={false}
        onAccept={onAccept}
      />,
    )
    const button = screen.getByRole('button', { name: /acknowledge and continue/i })
    expect(button).toBeDisabled()
    await user.click(screen.getByLabelText(/I am a tutor/i))
    await user.click(screen.getByLabelText(/no refund/i))
    expect(button).toBeDisabled()
    await user.click(screen.getByLabelText(/25%/i))
    expect(button).toBeEnabled()
    await user.click(button)
    expect(onAccept).toHaveBeenCalledOnce()
  })
})
