import React from 'react'
import Link from 'next/link'

const Navbar = () => {
  return (
    <nav className='fixed h-16 w-screen px-10 bg-black/40 backdrop-blur-md border-b border-zinc-800/40 z-[9999] text-zinc-300'>
      <div className='flex h-full items-center justify-between max-w-6xl mx-auto'>
        <Link href="/" className='text-lg font-semibold bg-gradient-to-r from-violet-400 to-fuchsia-400 bg-clip-text text-transparent cursor-pointer hover:scale-105 transition-all duration-200'>
          TBuddy
        </Link>
        <div className='flex flex-row gap-x-8 items-center'>
          <Link href="/" className='cursor-pointer hover:scale-105 transition-all duration-200 hover:text-white'>
            Home
          </Link>
          <div className='cursor-pointer hover:scale-105 transition-all duration-200 hover:text-zinc-100 hidden md:block'>Services</div>
          <div className='cursor-pointer hover:scale-105 transition-all duration-200 hover:text-zinc-100 hidden md:block'>About us</div>
          <div className='cursor-pointer hover:scale-105 transition-all duration-200 hover:text-zinc-100 hidden md:block'>Pricing</div>
        </div>
      </div>
    </nav>
  )
}

export default Navbar
