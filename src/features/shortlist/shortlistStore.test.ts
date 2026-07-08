import { describe, expect, it, beforeEach } from 'vitest'
import { addToShortlist, getShortlist, removeFromShortlist } from './shortlistStore'

describe('shortlistStore', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('adds and removes tutor ids', () => {
    expect(getShortlist().tutorIds).toEqual([])
    addToShortlist('t1')
    addToShortlist('t2')
    expect(getShortlist().tutorIds).toEqual(['t2', 't1'])
    removeFromShortlist('t1')
    expect(getShortlist().tutorIds).toEqual(['t2'])
  })
})

