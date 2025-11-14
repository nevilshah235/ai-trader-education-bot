import React from 'react';
import { CurrencyIcon } from '@/components/currency/currency-icon';

type TAccountInfoIcon = {
    is_virtual?: boolean;
    currency?: string;
};

const AccountInfoIcon = ({ is_virtual, currency }: TAccountInfoIcon) => {
    return (
        <span className='acc-info__id-icon'>
            <CurrencyIcon currency={currency} isVirtual={is_virtual} />
        </span>
    );
};

export default AccountInfoIcon;
