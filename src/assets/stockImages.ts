// Stock images (local) to make the UI more engaging.
// Files live under: public/assets/stock/*

import { publicUrl } from '../lib/publicUrl'

export const heroImages = [publicUrl('/assets/stock/hero-1.jpg'), publicUrl('/assets/stock/hero-2.jpg')]

export const categoryTiles: Array<{ title: string; subject: string; imageUrl: string }> = [
  {
    title: 'Maths tutors',
    subject: 'Maths',
    imageUrl: publicUrl('/assets/stock/cat-maths.jpg'),
  },
  {
    title: 'Science tutors',
    subject: 'Science',
    imageUrl: publicUrl('/assets/stock/cat-science.jpg'),
  },
  {
    title: 'English tutors',
    subject: 'English',
    imageUrl: publicUrl('/assets/stock/cat-english.jpg'),
  },
  {
    title: 'Computer Science',
    subject: 'Computer Science',
    imageUrl: publicUrl('/assets/stock/cat-cs.jpg'),
  },
  {
    title: 'Languages',
    subject: 'French',
    imageUrl: publicUrl('/assets/stock/cat-languages.jpg'),
  },
  {
    title: 'Music',
    subject: 'Guitar',
    imageUrl: publicUrl('/assets/stock/cat-music.jpg'),
  },
]

// People portraits for tutor cards (1:1 crop).
export const tutorPortraits = [
  publicUrl('/assets/stock/tutor-01.jpg'),
  publicUrl('/assets/stock/tutor-02.jpg'),
  publicUrl('/assets/stock/tutor-03.jpg'),
  publicUrl('/assets/stock/tutor-04.jpg'),
  publicUrl('/assets/stock/tutor-05.jpg'),
  publicUrl('/assets/stock/tutor-06.jpg'),
  publicUrl('/assets/stock/tutor-07.jpg'),
  publicUrl('/assets/stock/tutor-08.jpg'),
]

// Misc gallery images (classroom, books, desk).
export const tutorGallery = [
  publicUrl('/assets/stock/gallery-1.jpg'),
  publicUrl('/assets/stock/gallery-2.jpg'),
  publicUrl('/assets/stock/gallery-3.jpg'),
  publicUrl('/assets/stock/gallery-4.jpg'),
  publicUrl('/assets/stock/gallery-5.jpg'),
]
