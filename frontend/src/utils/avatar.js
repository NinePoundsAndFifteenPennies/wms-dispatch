import defaultAvatarImage from '../assets/images/default-avatar.svg'

export function getAvatarUrl(avatar) {
  return avatar || defaultAvatarImage
}

export { defaultAvatarImage }
