import type { IconName } from './Icon';
/** Mono uppercase status / promotion tag. Always text — never colour alone. Show at most two prominent badges per product image. */
export interface BadgeProps {
  /** new · offer / bogo: burgundy fill · shipping: burgundy-ink outline · limited: strong outline · low: warning outline · soldout: muted · drop: accent outline · outline: neutral */
  tone?: 'new' | 'offer' | 'bogo' | 'shipping' | 'limited' | 'low' | 'soldout' | 'outline' | 'drop';
  pill?: boolean;
  icon?: IconName;
  children?: React.ReactNode;
  className?: string;
}
export declare function Badge(props: BadgeProps): JSX.Element;
